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
MASTER_DEFAULTS = {'level': 1.0, 'blackout': 0.0, 'flash': 0.0, 'saturation': 1.0,
				   'trails': 0.0, 'trailszoom': 0.0, 'trailswarp': 0.0, 'trailscolour': 0.0,
				   'blur': 0.0, 'glitch': 0.0, 'outline': 0.0, 'melt': 0.0}
# Show controls that are not visuals. mapping.preset: a MIDI 'set' to 1-4
# switches the mapping page to preset A-D at that moment of the song (0 = no
# switch yet). Like every value it is replayed from the timeline, so seeking
# lands on the right preset.
CONTROL_DEFAULTS = {'mapping.preset': 0.0}
LAYER_PARAMS = tuple(LAYER_DEFAULTS)
MASTER_PARAMS = tuple(MASTER_DEFAULTS)


def defaultBase(num_layers=4):
	"""Base values used when a layer or the master controls are missing."""
	base = {'layer%d.%s' % (i, p): v for i in range(1, num_layers + 1) for p, v in LAYER_DEFAULTS.items()}
	base.update({'master.%s' % p: v for p, v in MASTER_DEFAULTS.items()})
	base.update(CONTROL_DEFAULTS)
	return base


def knownParams(num_layers=4, extra=()):
	"""Every assignable parameter name, e.g. 'layer1.opacity', 'master.flash', then extra (instrument targets)."""
	names = ['layer%d.%s' % (i, p) for i in range(1, num_layers + 1) for p in LAYER_PARAMS]
	return names + ['master.%s' % p for p in MASTER_PARAMS] + list(CONTROL_DEFAULTS) + list(extra)


# ---------------------------------------------------------------- instruments
# The instrument contract: any COMP inside visuals with a custom page named
# 'Instrument' is an instrument. Its number, toggle and menu parameters on that
# page are its settings: each one is a target '<instrument>.<parameter>' (lower
# case, e.g. particles.energy) for MIDI and the mapping page, and the engine
# publishes its value as the channel <instrument>_<parameter>. A 'Visible'
# toggle makes MIDI show / hide / toggle work on the bare name ('particles').

INSTRUMENT_PAGE = 'Instrument'
INSTRUMENT_STYLES = ('Float', 'Int', 'Toggle', 'Menu')
INSTRUMENT_SKIP = ('Preset',)  # applying a preset sets the other parameters; never a target
RESERVED_NAMES = ('master', 'mapping', 'clock')


def instrumentTargets(instruments):
	"""Targets of the instruments -> {target: (low, high)}, in page order.

	instruments: [(instrument name, [(parameter name, style, low, high), ...])],
	low / high being the slider range (a menu: 0 to its last index). Parameters
	of another style, skipped ones and instruments with a reserved or layer
	name are left out.
	"""
	targets = {}
	for name, pars in instruments:
		name = str(name).lower()
		if name in RESERVED_NAMES or name.startswith('layer') or not name.isidentifier():
			continue
		for par_name, style, low, high in pars:
			if style not in INSTRUMENT_STYLES or par_name in INSTRUMENT_SKIP:
				continue
			targets['%s.%s' % (name, par_name.lower())] = (float(low), float(high))
	return targets


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


NOTE_NAMES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')


def noteName(note):
	"""60 -> 'C4' (the common convention; some DAWs, e.g. Ableton, call 60 'C3')."""
	return '%s%d' % (NOTE_NAMES[note % 12], note // 12 - 1)


def recentNotes(note_ons, t, hold):
	"""Notes that started within the last hold seconds before t: [(note, age)], oldest first.

	Used by the MIDI monitor. Like evaluate, it depends only on the playback
	position, so seeking shows exactly what is due there.
	"""
	recent = [(t - start, note) for start, note in note_ons if 0.0 <= t - start < hold]
	recent.sort(key=lambda item: (-item[0], item[1]))
	return [(note, age) for age, note in recent]


# ---------------------------------------------------------------- triggers
# A trigger row (mapping page, Triggers) makes the Trigger Shape instrument
# react to an event: a MIDI note of the song, or a wearable's hit or button.
# Every event starts an action that settles by itself, so a trigger reads as
# a beat, not a switch:
#   pulse  the size swells by amount (0.5 = half as big again) and falls back
#   spin   turns by amount degrees, eased
#   sides  adds amount sides (3-12, wrapping round)
#   jump   glides to a new place, up to amount away from its position (the
#          same note at the same moment always lands on the same place)
#   flash  goes towards the Flash colour (amount = how far) and fades back
# MIDI events are worked out from the playback position, like the MIDI table,
# so seeking and Reset land on the right state. Wearable events are live.

TRIGGER_INSTRUMENT = 'trigger'
TRIGGER_ACTIONS = ('pulse', 'spin', 'sides', 'jump', 'flash')
TRIGGER_COLUMNS = ('preset', 'slot', 'on', 'when', 'note', 'does', 'amount')
PULSE_S = 0.4
SPIN_S = 0.3
JUMP_S = 0.15
FLASH_S = 0.6
SIDES_RANGE = (3, 12)
# Any instrument: 'burst:<instrument>.<setting>' jumps the setting by amount and
# lets it fall back over BURST_S; 'count:<instrument>.<name>' adds 1 to a counter
# value the instrument watches (Media: next file ...). Only connection slots
# 1-NUM_CONNECTIONS act; slots 5-8 stay in the table, unused.
BURST_S = 0.6
NUM_CONNECTIONS = 4
COUNT_TARGETS = ('media.restartcount', 'media.nextcount', 'media.randomcount', 'tiles.shufflecount')


def _isAction(action):
	return action in TRIGGER_ACTIONS or (action.startswith(('burst:', 'count:')) and '.' in action)
# Mapping presets are the phases: '1' ... '10'. Letters A-D from older shows read as 1-4.
PRESET_LETTERS = tuple(str(i) for i in range(1, 11))
_OLD_LETTERS = {'A': '1', 'B': '2', 'C': '3', 'D': '4'}


def emptyEffects():
	return {'pulse': 0.0, 'spin': 0.0, 'steps': 0, 'jumpx': 0.0, 'jumpy': 0.0, 'flash': 0.0, 'bursts': {}, 'counts': {}}


def _unit(seed, k):
	"""A repeatable pseudo-random number in -1..1 for a seed."""
	x = math.sin(seed * 12.9898 + k * 78.233) * 43758.5453
	return (x - math.floor(x)) * 2.0 - 1.0


def _ease(x):
	x = min(1.0, max(0.0, x))
	return x * x * (3.0 - 2.0 * x)


def jumpTarget(seed, amount):
	"""Where a jump goes, relative to the shape's own position."""
	return amount * _unit(seed, 1), amount * _unit(seed, 2)


def parseTriggers(rows):
	"""Trigger table rows (header first) -> {preset: [(when, note, action, amount, slot)]}: rows that are on and valid."""
	header = [str(c).strip().lower() for c in rows[0]] if rows else []
	col = {name: header.index(name) for name in TRIGGER_COLUMNS if name in header}
	found = {p: [] for p in PRESET_LETTERS}
	for row in rows[1:]:
		cell = lambda name: str(row[col[name]]).strip() if name in col and col[name] < len(row) else ''
		try:
			on = float(cell('on') or 0)
			note = int(float(cell('note') or 0))
			amount = float(cell('amount') or 0)
			slot = int(float(cell('slot') or 0))
		except ValueError:
			continue
		preset, when, action = cell('preset').upper(), cell('when'), cell('does')
		action = action if action.startswith(('burst:', 'count:')) else action.lower()
		preset = _OLD_LETTERS.get(preset, preset)
		if not on or preset not in found or not _isAction(action) or not when or not 1 <= slot <= NUM_CONNECTIONS:
			continue
		if when == 'midi' and not 0 <= note <= 127:
			continue
		found[preset].append((when, note, action, amount, slot))
	return found


def presetSwitches(events):
	"""[(time, preset)] from the MIDI events that set mapping.preset (1-10), in time order."""
	switches = []
	for te, _row, a in events:
		index = int(round(a.value))
		if a.param == 'mapping.preset' and a.action in ('set', 'fade') and 1 <= index <= len(PRESET_LETTERS):
			switches.append((te, PRESET_LETTERS[index - 1]))
	return switches


def presetAt(switches, t, start):
	"""The preset in use at time t: the last switch at or before t, else start."""
	current = start
	for te, preset in switches:
		if te > t:
			break
		current = preset
	return current


def midiTriggerEvents(note_ons, triggers, switches, start):
	"""Song triggers -> [(time, action, amount, seed)] in time order.

	note_ons: (seconds, note). triggers: parseTriggers output. Each note uses
	the rows of the preset in use at that moment (switches, else start).
	"""
	events = []
	for te, note in sorted(note_ons):
		for when, n, action, amount, slot in triggers.get(presetAt(switches, te, start), ()):
			if when == 'midi' and n == note:
				events.append((te, action, amount, round(te, 4) * 1000.0 + slot))
	return events


def triggerEffects(events, t, start=None):
	"""The effects at time t of events [(time, action, amount, seed)] in time order (later ones are ignored).

	start: effects already folded in (live triggers), its jump position included.
	"""
	fx = dict(start) if start else emptyEffects()
	fx['bursts'] = {}
	fx['counts'] = dict(fx.get('counts', {}))
	jump_from = jump_to = (fx['jumpx'], fx['jumpy'])
	jump_age = None
	for te, action, amount, seed in events:
		if te > t:
			break
		age = t - te
		if action == 'pulse':
			if age < PULSE_S:
				fx['pulse'] += amount * (1.0 - age / PULSE_S) ** 2
		elif action == 'spin':
			fx['spin'] += amount * _ease(age / SPIN_S)
		elif action == 'sides':
			fx['steps'] += int(round(amount))
		elif action == 'jump':
			jump_from, jump_to, jump_age = jump_to, jumpTarget(seed, amount), age
		elif action == 'flash':
			if age < FLASH_S:
				fx['flash'] = max(fx['flash'], amount * (1.0 - age / FLASH_S))
		elif action.startswith('burst:'):
			if age < BURST_S:
				target = action[len('burst:'):]
				fx['bursts'][target] = fx['bursts'].get(target, 0.0) + amount * (1.0 - age / BURST_S) ** 2
		elif action.startswith('count:'):
			target = action[len('count:'):]
			fx['counts'][target] = fx['counts'].get(target, 0) + 1
	if jump_age is not None:
		f = _ease(jump_age / JUMP_S)
		fx['jumpx'] = jump_from[0] + (jump_to[0] - jump_from[0]) * f
		fx['jumpy'] = jump_from[1] + (jump_to[1] - jump_from[1]) * f
	return fx


def addEffects(a, b):
	"""Song and live effects together: pulses, spins, steps and jumps add up; the stronger flash wins."""
	merged = lambda x, y: {k: x.get(k, 0) + y.get(k, 0) for k in set(x) | set(y)}
	return {'pulse': a['pulse'] + b['pulse'], 'spin': a['spin'] + b['spin'], 'steps': a['steps'] + b['steps'],
		'jumpx': a['jumpx'] + b['jumpx'], 'jumpy': a['jumpy'] + b['jumpy'], 'flash': max(a['flash'], b['flash']),
		'bursts': merged(a.get('bursts', {}), b.get('bursts', {})), 'counts': merged(a.get('counts', {}), b.get('counts', {}))}


def applyTriggerEffects(state, fx, name=TRIGGER_INSTRUMENT):
	"""Put the effects on the Trigger Shape's values in state (nothing happens without the instrument)."""
	for target, value in fx.get('bursts', {}).items():
		if target in state:
			state[target] += value
	for target in COUNT_TARGETS:
		if any(k.startswith(target.split('.')[0] + '.') for k in state):
			state[target] = float(fx.get('counts', {}).get(target, 0))
	key = lambda p: '%s.%s' % (name, p)
	if key('size') not in state:
		return state
	state[key('size')] = state[key('size')] * (1.0 + fx['pulse'])
	state[key('rotate')] = state.get(key('rotate'), 0.0) + fx['spin']
	low, high = SIDES_RANGE
	sides = min(high, max(low, int(round(state.get(key('sides'), low)))))
	state[key('sides')] = float(low + (sides - low + fx['steps']) % (high - low + 1))
	state[key('x')] = state.get(key('x'), 0.0) + fx['jumpx']
	state[key('y')] = state.get(key('y'), 0.0) + fx['jumpy']
	state[key('flash')] = min(1.0, max(state.get(key('flash'), 0.0), fx['flash']))
	return state


class LiveTriggers:
	"""Triggers from live signals (wearable hit / button): an event on each rising edge past 0.5.

	Events older than FOLD_S are folded into running totals, so the list
	stays short however long the show runs.
	"""

	FOLD_S = 2.0

	def __init__(self):
		self._previous = {}
		self._events = []
		self._start = emptyEffects()
		self._count = 0

	def update(self, rows, signals, now):
		"""rows: [(signal, action, amount, slot)] of the preset in use. signals: {name: value}."""
		names = {r[0] for r in rows}
		rising = set()
		for name in names:
			if name not in signals:
				continue
			value = float(signals[name])
			if value >= 0.5 and self._previous.get(name, 0.0) < 0.5:
				rising.add(name)
			self._previous[name] = value
		for name in list(self._previous):
			if name not in names or name not in signals:
				del self._previous[name]
		for signal, action, amount, slot in rows:
			if signal in rising:
				self._count += 1
				self._events.append((now, action, amount, self._count * 31.0 + slot))
		while self._events and now - self._events[0][0] > self.FOLD_S:
			_te, action, amount, seed = self._events.pop(0)
			if action == 'spin':
				self._start['spin'] += amount
			elif action == 'sides':
				self._start['steps'] += int(round(amount))
			elif action == 'jump':
				self._start['jumpx'], self._start['jumpy'] = jumpTarget(seed, amount)
			elif action.startswith('count:'):
				target = action[len('count:'):]
				self._start['counts'][target] = self._start['counts'].get(target, 0) + 1

	def effects(self, now):
		return triggerEffects(self._events, now, self._start)
