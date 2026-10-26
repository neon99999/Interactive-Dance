"""Show logic: turn MIDI assignments and input assignments into visual state.

Pure Python with no TouchDesigner imports, so it runs inside TD (engine) and
in plain Python unit tests (tests/test_show_logic.py).

The visual state at a playback time is computed from the MIDI timeline, not
from live callbacks: every Note On before the time is replayed in order. So
pausing never repeats an action, and seeking or resetting restores the right
state.
"""

import math

ACTIONS = ('show', 'hide', 'toggle', 'trigger', 'fade', 'set')
ACTION_ALIASES = {'set value': 'set', 'setvalue': 'set', 'set_value': 'set'}
TRIGGER_DEFAULT_S = 0.2

LAYER_DEFAULTS = {'visible': 0.0, 'opacity': 1.0, 'red': 1.0, 'green': 1.0, 'blue': 1.0,
				  'scale': 1.0, 'x': 0.0, 'y': 0.0, 'rotate': 0.0, 'content': 0.0, 'effect': 0.0}
MASTER_DEFAULTS = {'level': 1.0, 'blackout': 0.0, 'flash': 0.0}
LAYER_PARAMS = tuple(LAYER_DEFAULTS)
MASTER_PARAMS = tuple(MASTER_DEFAULTS)


def defaultBase(num_layers=4):
	"""Base values used when a layer or the master controls are missing."""
	base = {'layer%d.%s' % (i, p): v for i in range(1, num_layers + 1) for p, v in LAYER_DEFAULTS.items()}
	base.update({'master.%s' % p: v for p, v in MASTER_DEFAULTS.items()})
	return base


def knownParams(num_layers=4):
	"""Every assignable parameter name, e.g. 'layer1.opacity', 'master.flash'."""
	names = ['layer%d.%s' % (i, p) for i in range(1, num_layers + 1) for p in LAYER_PARAMS]
	return names + ['master.%s' % p for p in MASTER_PARAMS]


class Assignment:
	"""One valid row of the MIDI assignment table."""

	def __init__(self, row, note, param, action, value, duration):
		self.row = row
		self.note = note
		self.param = param
		self.action = action
		self.value = value
		self.duration = duration

	def __repr__(self):
		return 'Assignment(row=%d, note=%d, %s %s %s %s)' % (
			self.row, self.note, self.action, self.param, self.value, self.duration)


def _cell(row, i):
	return str(row[i]).strip() if i < len(row) else ''


def _number(text, label, errors, where):
	try:
		value = float(text)
	except ValueError:
		errors.append('%s: %s "%s" is not a number' % (where, label, text))
		return None
	if math.isnan(value) or math.isinf(value):
		errors.append('%s: %s "%s" is not a usable number' % (where, label, text))
		return None
	return value


def resolveTarget(target, known):
	"""'layer1' -> 'layer1.visible'; returns None if the target is unknown."""
	name = target.strip().lower().replace(' ', '')
	if name and '.' not in name:
		name += '.visible'
	return name if name in known else None


def parseAssignments(rows, known=None):
	"""Validate MIDI assignment rows -> (assignments, errors).

	rows: table rows as lists of strings, the first row being the header
	(note, target, action, value, duration). Blank rows are skipped; invalid
	rows are reported in errors and skipped, never raised.
	"""
	known = set(known or knownParams())
	header = [str(c).strip().lower() for c in rows[0]] if rows else []
	col = {name: header.index(name) for name in ('note', 'target', 'action', 'value', 'duration')
		   if name in header}
	assignments, errors = [], []
	for r, row in enumerate(rows[1:], start=1):
		cells = {name: _cell(row, i) for name, i in col.items()}
		if not any(cells.values()):
			continue
		where = 'row %d' % r
		note = _number(cells.get('note', ''), 'note', errors, where)
		if note is None:
			continue
		if note != int(note) or not 0 <= note <= 127:
			errors.append('%s: note "%s" must be a whole number 0-127' % (where, cells['note']))
			continue
		action = cells.get('action', '').lower()
		action = ACTION_ALIASES.get(action, action)
		if action not in ACTIONS:
			errors.append('%s: unknown action "%s" (use %s)' % (where, cells.get('action', ''), ', '.join(ACTIONS)))
			continue
		param = resolveTarget(cells.get('target', ''), known)
		if param is None:
			errors.append('%s: unknown target "%s"' % (where, cells.get('target', '')))
			continue
		value_text = cells.get('value', '')
		if value_text:
			value = _number(value_text, 'value', errors, where)
			if value is None:
				continue
		elif action in ('fade', 'set'):
			errors.append('%s: action "%s" needs a value' % (where, action))
			continue
		else:
			value = {'show': 1.0, 'hide': 0.0, 'trigger': 1.0}.get(action, 0.0)
		if action == 'show':
			value = 1.0
		elif action == 'hide':
			value = 0.0
		duration_text = cells.get('duration', '')
		if duration_text:
			duration = _number(duration_text, 'duration', errors, where)
			if duration is None:
				continue
			if duration < 0:
				errors.append('%s: duration "%s" cannot be negative' % (where, duration_text))
				continue
		else:
			duration = TRIGGER_DEFAULT_S if action == 'trigger' else 0.0
		if action == 'trigger' and duration <= 0:
			duration = TRIGGER_DEFAULT_S
		assignments.append(Assignment(r, int(note), param, action, value, duration))
	return assignments, errors


def buildEvents(note_ons, assignments):
	"""Pair every Note On with its assignments -> [(time, row, assignment)].

	note_ons: (seconds, note) pairs. Events are sorted by time, then by table
	row, so at the same moment a later row overrides an earlier one.
	"""
	by_note = {}
	for a in assignments:
		by_note.setdefault(a.note, []).append(a)
	events = [(t, a.row, a) for t, note in note_ons for a in by_note.get(note, ())]
	events.sort(key=lambda e: (e[0], e[1]))
	return events


class _Ramp:
	"""A persistent value moving from start to end over [t0, t0 + duration]."""

	__slots__ = ('t0', 'start', 'end', 'duration')

	def __init__(self, t0, start, end, duration):
		self.t0, self.start, self.end, self.duration = t0, start, end, duration

	def at(self, t):
		if self.duration <= 0 or t >= self.t0 + self.duration:
			return self.end
		if t <= self.t0:
			return self.start
		return self.start + (self.end - self.start) * (t - self.t0) / self.duration


def evaluate(events, base, t):
	"""Visual state at time t: {param: value}, starting from base values.

	Persistent actions (show, hide, toggle, fade, set) are replayed in order.
	A trigger only applies while t is inside its duration, then the value
	falls back to what the persistent actions say. Pure function of t.
	"""
	ramps = {}
	triggers = {}
	for te, _row, a in events:
		if te > t:
			break
		if a.action == 'trigger':
			if t < te + a.duration:
				triggers[a.param] = a.value
			continue
		ramp = ramps.get(a.param)
		current = ramp.at(te) if ramp else base.get(a.param, 0.0)
		if a.action == 'toggle':
			destination = ramp.end if ramp else base.get(a.param, 0.0)
			target = 0.0 if destination >= 0.5 else 1.0
		else:
			target = a.value
		ramps[a.param] = _Ramp(te, current, target, a.duration)
	state = dict(base)
	for param, ramp in ramps.items():
		state[param] = ramp.at(t)
	state.update(triggers)
	return state


# ---------------------------------------------------------------- inputs

class InputAssignment:
	"""One valid row of the input assignment table."""

	def __init__(self, row, signal, param, in_min, in_max, out_min, out_max, smoothing):
		self.row = row
		self.signal = signal
		self.param = param
		self.in_min, self.in_max = in_min, in_max
		self.out_min, self.out_max = out_min, out_max
		self.smoothing = smoothing

	def map(self, x):
		"""Scale x from the input range to the output range, clamped."""
		f = (x - self.in_min) / (self.in_max - self.in_min)
		f = min(1.0, max(0.0, f))
		return self.out_min + (self.out_max - self.out_min) * f


def parseInputAssignments(rows, known=None):
	"""Validate input assignment rows -> (assignments, errors).

	Columns: signal, target, in_min, in_max, out_min, out_max, smoothing.
	Blank range cells default to 0-1; blank smoothing to 0 (none).
	"""
	known = set(known or knownParams())
	header = [str(c).strip().lower() for c in rows[0]] if rows else []
	names = ('signal', 'target', 'in_min', 'in_max', 'out_min', 'out_max', 'smoothing')
	col = {name: header.index(name) for name in names if name in header}
	defaults = {'in_min': 0.0, 'in_max': 1.0, 'out_min': 0.0, 'out_max': 1.0, 'smoothing': 0.0}
	assignments, errors = [], []
	for r, row in enumerate(rows[1:], start=1):
		cells = {name: _cell(row, i) for name, i in col.items()}
		if not any(cells.values()):
			continue
		where = 'row %d' % r
		signal = cells.get('signal', '')
		if not signal:
			errors.append('%s: no signal name' % where)
			continue
		param = resolveTarget(cells.get('target', ''), known)
		if param is None:
			errors.append('%s: unknown target "%s"' % (where, cells.get('target', '')))
			continue
		nums = {}
		for name, default in defaults.items():
			text = cells.get(name, '')
			nums[name] = default if not text else _number(text, name, errors, where)
		if None in nums.values():
			continue
		if nums['in_min'] == nums['in_max']:
			errors.append('%s: in_min and in_max cannot be equal' % where)
			continue
		if nums['smoothing'] < 0:
			errors.append('%s: smoothing cannot be negative' % where)
			continue
		assignments.append(InputAssignment(r, signal, param, nums['in_min'], nums['in_max'],
										   nums['out_min'], nums['out_max'], nums['smoothing']))
	return assignments, errors


class InputMapper:
	"""Applies input assignments each frame, with per-row smoothing."""

	def __init__(self):
		self._smoothed = {}

	def apply(self, assignments, signals, state, dt):
		"""Override state params from signals; missing signals are skipped.

		signals: {name: value}. Rows are applied in order, so for the same
		target a later row wins. Returns the updated state dict.
		"""
		live = set()
		for a in assignments:
			if a.signal not in signals:
				continue
			target = a.map(float(signals[a.signal]))
			key = (a.row, a.signal, a.param)
			live.add(key)
			previous = self._smoothed.get(key)
			if previous is None or a.smoothing <= 0 or dt <= 0:
				value = target
			else:
				value = previous + (target - previous) * (1.0 - math.exp(-dt / a.smoothing))
			self._smoothed[key] = value
			state[a.param] = value
		for key in list(self._smoothed):
			if key not in live:
				del self._smoothed[key]
		return state
