"""Phases: the piece in up to 8 phases, each with up to 8 placeholder events.

Pure Python with no TouchDesigner imports, so it is unit-tested in plain
Python (tests/test_phases.py). PhasesExt (the phases component) holds the
parameters and the table; the event_state table it writes every frame is
drawn by the Phase Events instrument (visuals/events).

A MIDI note of the song can start each phase (Note for Phase 1-8). In a
phase, each event is a named shape (rectangle, circle or triangle):
  Show always   on screen for the whole phase
  Show toggle   its trigger makes it appear, the same trigger again hides it
  Show timed    its trigger makes it appear for Time seconds (again: restart)
The trigger is a MIDI note of the song or a wearable's hit or button.
Two links per event let a continuous input (arm tilt, body position, ...)
move one property (size, x, y, rotation, brightness) between From and To,
while the event is on screen. Events fade in and out over FADE_S.
"""

NUM_PHASES = 8
NUM_EVENTS = 8
NUM_LINKS = 2
FADE_S = 0.3
LINK_SMOOTH_S = 0.1
WEARABLES = (1, 2, 3)

SHAPES = ('rectangle', 'circle', 'triangle')
SHOW_MODES = ('always', 'toggle', 'timed')
COLOURS = ('white', 'red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'magenta')
PROPERTIES = ('size', 'x', 'y', 'rotate', 'bright')
# Natural From / To of each property, used when a link gets a new property.
PROPERTY_RANGES = {'size': (0.1, 0.8), 'x': (-0.8, 0.8), 'y': (-0.8, 0.8), 'rotate': (-180.0, 180.0),
	'bright': (0.2, 1.0)}
TRIGGER_SIGNALS = ('hit', 'btn')
# Continuous inputs offered for links, in menu order (others can be typed).
LINK_SIGNALS = ('pose_x', 'pose_hand_l', 'pose_hand_r', 'pose_spread', 'pose_energy') + tuple(
	'serial_w%d_%s' % (w, s) for w in WEARABLES for s in ('roll', 'pitch', 'act', 'gx', 'gy', 'gz')) + (
	'camera_motion', 'camera_left', 'camera_right', 'sim_level')

LINK_FIELDS = tuple('link%d%s' % (k, f) for k in range(1, NUM_LINKS + 1) for f in ('in', 'prop', 'from', 'to'))
EVENT_FIELDS = ('on', 'name', 'shape', 'colour', 'x', 'y', 'size', 'show', 'time', 'trigger', 'note') + LINK_FIELDS
TEXT_FIELDS = ('name', 'shape', 'colour', 'show', 'trigger') + tuple(
	f for f in LINK_FIELDS if f.endswith(('in', 'prop')))
COLUMNS = ('phase', 'event') + EVENT_FIELDS
DEFAULTS = {'on': 0.0, 'name': '', 'shape': 'rectangle', 'colour': 'white', 'x': 0.0, 'y': 0.0, 'size': 0.3,
	'show': 'timed', 'time': 1.0, 'trigger': 'none', 'note': 60.0}
for _k in range(1, NUM_LINKS + 1):
	DEFAULTS.update({'link%din' % _k: 'none', 'link%dprop' % _k: 'rotate',
		'link%dfrom' % _k: PROPERTY_RANGES['rotate'][0], 'link%dto' % _k: PROPERTY_RANGES['rotate'][1]})
SIDES = {'rectangle': 4, 'circle': 0, 'triangle': 3}


def triggerSources():
	"""What can trigger an event, in menu order: nothing, a MIDI note, each wearable's hit and button."""
	return ['none', 'midi'] + ['serial_w%d_%s' % (w, s) for w in WEARABLES for s in TRIGGER_SIGNALS]


def linkSources():
	return ['none'] + list(LINK_SIGNALS)


def propertyRange(prop):
	return PROPERTY_RANGES.get(prop, (0.0, 1.0))


def _number(text, default):
	try:
		return float(text)
	except (TypeError, ValueError):
		return default


def _text(value):
	return value if isinstance(value, str) else '%g' % value


def emptyEvents():
	return [dict(DEFAULTS) for _ in range(NUM_EVENTS)]


def readPhases(rows):
	"""Phase table rows (header first) -> {1..8: [event dicts]}, every phase with NUM_EVENTS events."""
	phases = {p: emptyEvents() for p in range(1, NUM_PHASES + 1)}
	header = [str(c).strip().lower() for c in rows[0]] if rows else []
	col = {name: header.index(name) for name in COLUMNS if name in header}
	for row in rows[1:]:
		cell = lambda name: str(row[col[name]]).strip() if name in col and col[name] < len(row) else ''
		phase = int(_number(cell('phase'), 0))
		event = int(_number(cell('event'), 0))
		if phase not in phases or not 1 <= event <= NUM_EVENTS:
			continue
		values = phases[phase][event - 1]
		for name in EVENT_FIELDS:
			text = cell(name)
			if text == '' and name != 'name':
				continue
			values[name] = text if name in TEXT_FIELDS else _number(text, DEFAULTS[name])
	return phases


def phaseRows(phases):
	"""{phase: [event dicts]} -> table rows (header first), one row per event."""
	rows = [list(COLUMNS)]
	for phase in range(1, NUM_PHASES + 1):
		for i, event in enumerate(phases.get(phase, emptyEvents())[:NUM_EVENTS], start=1):
			rows.append([str(phase), str(i)] + [_text(event.get(name, DEFAULTS[name])) for name in EVENT_FIELDS])
	return rows


def phaseSwitches(note_ons, phase_notes):
	"""[(time, phase)] in time order: the song's notes that start a phase. phase_notes: {phase: note}."""
	by_note = {}
	for phase, note in phase_notes.items():
		if 0 <= note <= 127:
			by_note.setdefault(int(note), phase)
	return sorted((t, by_note[note]) for t, note in note_ons if note in by_note)


def phaseAt(switches, t):
	"""The phase at time t: the last switch at or before t, or None before the first one."""
	current = None
	for te, phase in switches:
		if te > t:
			break
		current = phase
	return current


def notesBetween(note_ons, t0, t1):
	"""Notes that start in (t0, t1]: what the song played since the last frame."""
	return [note for t, note in note_ons if t0 < t <= t1]


class _Slot:
	__slots__ = ('shown', 'until', 'alpha', 'smooth')

	def __init__(self):
		self.shown, self.until, self.alpha, self.smooth = False, None, 0.0, {}


class PhaseRunner:
	"""The live state of the current phase's events, one call per frame."""

	def __init__(self):
		self.phase = None
		self.slots = [_Slot() for _ in range(NUM_EVENTS)]
		self.prev = {}

	def fired(self, signals, notes):
		"""{trigger source}: wearable signals that rose past 0.5 since the last frame, and 'midi:<note>'."""
		out = {'midi:%d' % n for n in notes}
		for name in triggerSources()[2:]:
			value = signals.get(name, 0.0)
			if value > 0.5 and self.prev.get(name, 0.0) <= 0.5:
				out.add(name)
			self.prev[name] = value
		return out

	def update(self, phase, events, signals, notes, now, dt, signal_range):
		"""Advance one frame. Returns one state dict per event slot.

		events: the phase's event dicts. notes: MIDI notes played since the last
		frame. signal_range(name) -> (low, high) of a continuous input.
		"""
		if phase != self.phase:
			self.phase = phase
			self.slots = [_Slot() for _ in range(NUM_EVENTS)]
		fired = self.fired(signals, notes)
		step = dt / FADE_S if FADE_S > 0 else 1.0
		out = []
		for slot, event in zip(self.slots, events):
			on = _number(event.get('on'), 0.0) >= 0.5
			mode = event.get('show', 'timed')
			trigger = event.get('trigger', 'none')
			key = 'midi:%d' % int(_number(event.get('note'), -1)) if trigger == 'midi' else trigger
			hit = on and trigger != 'none' and key in fired
			if mode == 'toggle' and hit:
				slot.shown = not slot.shown
			elif mode == 'timed' and hit:
				slot.until = now + max(0.0, _number(event.get('time'), 1.0))
			if not on:
				target = 0.0
			elif mode == 'always':
				target = 1.0
			elif mode == 'toggle':
				target = 1.0 if slot.shown else 0.0
			else:
				target = 1.0 if slot.until is not None and now < slot.until else 0.0
			if target > slot.alpha:
				slot.alpha = min(target, slot.alpha + step)
			else:
				slot.alpha = max(target, slot.alpha - step)
			values = {'size': _number(event.get('size'), 0.3), 'x': _number(event.get('x'), 0.0),
				'y': _number(event.get('y'), 0.0), 'rotate': 0.0, 'bright': 1.0}
			for k in range(1, NUM_LINKS + 1):
				name = event.get('link%din' % k, 'none')
				prop = event.get('link%dprop' % k, '')
				if name in ('', 'none') or prop not in values or name not in signals:
					continue
				low, high = signal_range(name)
				f = (signals[name] - low) / (high - low) if high != low else 0.0
				f = min(1.0, max(0.0, f))
				lo, hi = _number(event.get('link%dfrom' % k), 0.0), _number(event.get('link%dto' % k), 1.0)
				goal = lo + (hi - lo) * f
				previous = slot.smooth.get(prop)
				if previous is None or LINK_SMOOTH_S <= 0:
					value = goal
				else:
					value = previous + (goal - previous) * min(1.0, dt / LINK_SMOOTH_S)
				slot.smooth[prop] = value
				values[prop] = value
			colour = event.get('colour', 'white')
			out.append(dict(values, alpha=slot.alpha, sides=SIDES.get(event.get('shape'), 4),
				shape=event.get('shape', 'rectangle'),
				colour=COLOURS.index(colour) if colour in COLOURS else 0, name=str(event.get('name', ''))))
		return out
