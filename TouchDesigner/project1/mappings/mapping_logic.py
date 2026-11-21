"""Mapping page logic: dancer-friendly mappings -> input assignment rows.

Pure Python with no TouchDesigner imports, so it is unit-tested in plain
Python (tests/test_mapping_logic.py). The mappings component (MappingsExt)
holds 8 mapping slots and one preset per phase (1-10) and uses this module to turn the
slots into rows for the engine, in the input assignment format:
  signal, target, in_min, in_max, out_min, out_max, smoothing

A slot names a movement signal and a visual target and gives the target's
From / To values. The signal's input range comes from the catalogue below,
so dancers never type sensor ranges; Sensitivity narrows it (2 = half the
movement reaches To).
"""

import re

NUM_SLOTS = 8
# One preset per phase. Shows saved before phases kept presets A-D: they read as phases 1-4.
PRESETS = tuple(str(i) for i in range(1, 11))
OLD_PRESETS = {'A': '1', 'B': '2', 'C': '3', 'D': '4'}
SLOT_FIELDS = ('on', 'signal', 'target', 'from', 'to', 'smooth', 'sens')
PRESET_COLUMNS = ('preset', 'slot') + SLOT_FIELDS
SLOT_DEFAULTS = {'on': 0.0, 'signal': '', 'target': '', 'from': 0.0, 'to': 1.0, 'smooth': 0.1, 'sens': 1.0}

# Movement signals offered in the menu, in menu order. Others (OSC addresses,
# serial values with other names) still work when typed in, with a 0-1 range.
POSE_SIGNALS = ('pose_present', 'pose_x', 'pose_hand_l', 'pose_hand_r', 'pose_spread', 'pose_energy',
	'pose_zone1', 'pose_zone2', 'pose_zone3', 'pose_zone4', 'pose_zone5')
WEARABLE_SIGNALS = ('act', 'gx', 'gy', 'gz', 'pitch', 'roll', 'hit', 'still', 'btn')
OTHER_SIGNALS = ('sim_level', 'sim_trigger', 'sim_zone', 'camera_motion', 'camera_left', 'camera_right')
WEARABLES = (1, 2, 3)

# Input ranges by signal. Wearable values are matched without their
# serial_wN_ prefix; gyro is degrees per second, tilt degrees.
WEARABLE_RANGES = {'gx': (-500.0, 500.0), 'gy': (-500.0, 500.0), 'gz': (-500.0, 500.0),
	'pitch': (-90.0, 90.0), 'roll': (-180.0, 180.0), 'hitdir': (0.0, 6.0), 'mode': (1.0, 2.0)}
_WEARABLE = re.compile(r'^serial_w\d+_(\w+)$')

# Natural From / To for each kind of visual value, used when a target is chosen.
TARGET_RANGES = {'saturation': (0.0, 2.0), 'scale': (0.5, 2.0), 'x': (-1.0, 1.0), 'y': (-1.0, 1.0), 'rotate': (0.0, 360.0),
	'content': (0.0, 6.0), 'effect': (0.0, 3.0)}
# Targets left out of the menu: switching presets from a movement would make
# the mappings change themselves.
HIDDEN_TARGETS = ('mapping.preset',)
# Whole-picture effects removed on 2026-11-20. A slot that still names one is cleared, not moved to another target.
REMOVED_TARGETS = ('master.trails', 'master.trailszoom', 'master.trailswarp', 'master.trailscolour', 'master.blur', 'master.melt')


def signalCatalogue():
	"""Every signal the menu offers, in order: pose, then wearables 1-3, then the others."""
	names = list(POSE_SIGNALS)
	for w in WEARABLES:
		names += ['serial_w%d_%s' % (w, s) for s in WEARABLE_SIGNALS]
	return names + list(OTHER_SIGNALS)


def targetCatalogue(known):
	"""The targets the menu offers: the engine's assignable values, minus hidden ones."""
	return [name for name in known if name not in HIDDEN_TARGETS]


def signalRange(name):
	"""(low, high) of a signal's useful values."""
	match = _WEARABLE.match(name)
	if match:
		return WEARABLE_RANGES.get(match.group(1), (0.0, 1.0))
	if name == 'pose_zone':
		return (0.0, 5.0)
	return (0.0, 1.0)


def targetRange(target, ranges=None):
	"""(from, to) that covers a target's useful values, e.g. layer1.rotate -> (0, 360).

	ranges: {target: (low, high)} given by the instruments (their slider
	ranges); those win over the layer table.
	"""
	if ranges and target in ranges:
		return tuple(ranges[target])
	return TARGET_RANGES.get(target.split('.')[-1], (0.0, 1.0))


def inputRange(signal, sensitivity):
	"""The signal range narrowed by sensitivity: around 0 for a signed signal, else from its low end."""
	low, high = signalRange(signal)
	sensitivity = sensitivity if sensitivity > 0 else 1.0
	if low < 0 < high:
		return low / sensitivity, high / sensitivity
	return low, low + (high - low) / sensitivity


def _number(text, default):
	try:
		return float(text)
	except (TypeError, ValueError):
		return default


def assignmentRows(slots, known=None):
	"""Engine rows (header first) for the slots that are on and complete.

	slots: dicts with SLOT_FIELDS. known: the engine's target names; a slot
	whose target is not among them is left out (the engine would reject it).
	"""
	rows = [['signal', 'target', 'in_min', 'in_max', 'out_min', 'out_max', 'smoothing']]
	for slot in slots:
		signal = str(slot.get('signal', '')).strip()
		target = str(slot.get('target', '')).strip()
		if not _number(slot.get('on'), 0.0) or not signal or not target:
			continue
		if known is not None and target not in known:
			continue
		low, high = inputRange(signal, _number(slot.get('sens'), 1.0))
		rows.append([signal, target, '%g' % low, '%g' % high,
			'%g' % _number(slot.get('from'), 0.0), '%g' % _number(slot.get('to'), 1.0),
			'%g' % max(0.0, _number(slot.get('smooth'), 0.0))])
	return rows


def emptySlots():
	return [dict(SLOT_DEFAULTS) for _ in range(NUM_SLOTS)]


def readPresets(rows):
	"""Preset table rows (header first) -> {preset: [slot dicts]}, every preset with NUM_SLOTS slots."""
	presets = {p: emptySlots() for p in PRESETS}
	header = [str(c).strip().lower() for c in rows[0]] if rows else []
	col = {name: header.index(name) for name in PRESET_COLUMNS if name in header}
	for row in rows[1:]:
		cell = lambda name: str(row[col[name]]).strip() if name in col and col[name] < len(row) else ''
		preset = cell('preset').upper()
		preset = OLD_PRESETS.get(preset, preset)
		slot = int(_number(cell('slot'), 0))
		if preset not in presets or not 1 <= slot <= NUM_SLOTS:
			continue
		values = presets[preset][slot - 1]
		for name in SLOT_FIELDS:
			text = cell(name)
			if text == '':
				continue
			values[name] = text if name in ('signal', 'target') else _number(text, SLOT_DEFAULTS[name])
		if values['target'] in REMOVED_TARGETS:
			values.update(on=0.0, target='')
	return presets


def presetRows(presets):
	"""{preset: [slot dicts]} -> table rows (header first), one row per slot."""
	rows = [list(PRESET_COLUMNS)]
	for preset in PRESETS:
		for i, slot in enumerate(presets.get(preset, emptySlots())[:NUM_SLOTS], start=1):
			rows.append([preset, str(i)] + [_text(slot.get(name, SLOT_DEFAULTS[name])) for name in SLOT_FIELDS])
	return rows


def _text(value):
	return value if isinstance(value, str) else '%g' % value


# ---------------------------------------------------------------- triggers
# 8 trigger rows per preset, kept with the mappings so one preset is "what
# everything does" in that part of the piece. The engine reads the stored
# table (show_logic.parseTriggers); the actions are described there.

NUM_TRIGGERS = 8
TRIGGER_FIELDS = ('on', 'when', 'note', 'does', 'amount')
TRIGGER_COLUMNS = ('preset', 'slot') + TRIGGER_FIELDS
TRIGGER_DEFAULTS = {'on': 0.0, 'when': 'midi', 'note': 60.0, 'does': 'pulse', 'amount': 0.5}
TRIGGER_ACTIONS = ('pulse', 'spin', 'sides', 'jump', 'flash')
TRIGGER_SIGNALS = ('hit', 'btn')
# By action: the amount a new trigger starts with, and the slider range.
TRIGGER_AMOUNTS = {'pulse': (0.5, 0.0, 2.0), 'spin': (45.0, -180.0, 180.0), 'sides': (1.0, -4.0, 4.0),
	'jump': (0.5, 0.0, 1.0), 'flash': (1.0, 0.0, 1.0)}
TRIGGER_TEXT = ('when', 'does')


def triggerSources():
	"""What a trigger can listen to (its When), in menu order: every Source + Input of the trigger menus."""
	names = []
	for source in TRIGGER_SOURCES:
		names += [joinSignal(source, name) for name in sourceInputs(source, trigger=True)]
	return names


def triggerAmount(action):
	"""(default, slider low, slider high) of an action's amount."""
	return TRIGGER_AMOUNTS.get(action, (0.5, 0.0, 1.0))


def emptyTriggers():
	return [dict(TRIGGER_DEFAULTS) for _ in range(NUM_TRIGGERS)]


def readTriggers(rows):
	"""Trigger table rows (header first) -> {preset: [trigger dicts]}, every preset with NUM_TRIGGERS rows."""
	presets = {p: emptyTriggers() for p in PRESETS}
	header = [str(c).strip().lower() for c in rows[0]] if rows else []
	col = {name: header.index(name) for name in TRIGGER_COLUMNS if name in header}
	for row in rows[1:]:
		cell = lambda name: str(row[col[name]]).strip() if name in col and col[name] < len(row) else ''
		preset = cell('preset').upper()
		preset = OLD_PRESETS.get(preset, preset)
		slot = int(_number(cell('slot'), 0))
		if preset not in presets or not 1 <= slot <= NUM_TRIGGERS:
			continue
		values = presets[preset][slot - 1]
		for name in TRIGGER_FIELDS:
			text = cell(name)
			if text == '':
				continue
			values[name] = text if name in TRIGGER_TEXT else _number(text, TRIGGER_DEFAULTS[name])
	return presets


def triggerRows(presets):
	"""{preset: [trigger dicts]} -> table rows (header first), one row per trigger."""
	rows = [list(TRIGGER_COLUMNS)]
	for preset in PRESETS:
		for i, trig in enumerate(presets.get(preset, emptyTriggers())[:NUM_TRIGGERS], start=1):
			rows.append([preset, str(i)] + [_text(trig.get(name, TRIGGER_DEFAULTS[name])) for name in TRIGGER_FIELDS])
	return rows


def presetFromMidi(value):
	"""The preset a MIDI 'mapping.preset' value selects ('1' ... '10'), or None for 0 / out of range."""
	index = int(round(value))
	return PRESETS[index - 1] if 1 <= index <= len(PRESETS) else None


# ---------------------------------------------------------------- the four menus
# A mapping is chosen in four short menus instead of two long ones:
#   Source (Wearable 1, Body, ...) -> Input (Tilt sideways, Hit, ...)  = the signal
#   Instrument (Particles, ...)    -> Setting (Size, ...)              = the target
# The stored slot keeps the signal and target names, so presets and shows
# do not change; the four menus are worked out from them.

SOURCES = ('wearable1', 'wearable2', 'wearable3', 'body', 'camera', 'test')
# Continuous inputs per kind of source (mappings), in menu order.
SOURCE_INPUTS = {
	'wearable': ('roll', 'pitch', 'act', 'gx', 'gy', 'gz', 'still', 'hit', 'btn'),
	'body': ('pose_x', 'pose_hand_l', 'pose_hand_r', 'pose_spread', 'pose_energy', 'pose_present',
		'pose_zone1', 'pose_zone2', 'pose_zone3', 'pose_zone4', 'pose_zone5'),
	'camera': ('camera_motion', 'camera_left', 'camera_right'),
	'test': ('sim_level', 'sim_trigger', 'sim_zone'),
}
# Inputs that make sense as a trigger (a moment: something starts), per kind of source.
TRIGGER_SOURCES = ('song', 'wearable1', 'wearable2', 'wearable3', 'body', 'test')
TRIGGER_INPUTS = {
	'song': ('midi',),
	'wearable': ('hit', 'btn', 'still'),
	'body': ('pose_present', 'pose_zone1', 'pose_zone2', 'pose_zone3', 'pose_zone4', 'pose_zone5'),
	'test': ('sim_trigger',),
}
# Settings never offered as a mapping target: compositing order and blend are
# fixed, Mix is gone, and a mapping must not switch the mappings themselves.
HIDDEN_SETTINGS = ('blend', 'order', 'mix', 'restartcount', 'nextcount', 'randomcount', 'shufflecount', 'refresh')
HIDDEN_INSTRUMENTS = ('mapping', 'events')
INSTRUMENT_ORDER = ('trigger', 'particles', 'noise', 'tiles', 'media', 'video', 'master', 'shapes', 'layer1', 'layer2', 'layer3', 'layer4')


def _kind(source):
	return 'wearable' if source.startswith('wearable') else source


def joinSignal(source, name):
	"""Source + input -> the signal name: ('wearable1', 'roll') -> 'serial_w1_roll'."""
	if not source or not name or name == 'none':
		return ''
	if source.startswith('wearable'):
		return 'serial_w%s_%s' % (source[len('wearable'):], name)
	return name


def splitSignal(signal):
	"""Signal name -> (source, input): 'serial_w1_roll' -> ('wearable1', 'roll'); unknown -> ('', signal)."""
	signal = str(signal or '').strip()
	if not signal:
		return '', ''
	match = re.match(r'^serial_w(\d+)_(\w+)$', signal)
	if match:
		return 'wearable' + match.group(1), match.group(2)
	if signal == 'midi':
		return 'song', 'midi'
	for source in ('body', 'camera', 'test'):
		if signal in SOURCE_INPUTS[source] or signal in TRIGGER_INPUTS.get(source, ()):
			return source, signal
	if signal.startswith('pose_'):
		return 'body', signal
	if signal.startswith('camera_'):
		return 'camera', signal
	if signal.startswith('sim_'):
		return 'test', signal
	return '', signal


def sourceInputs(source, trigger=False):
	"""The inputs a source offers: continuous ones for a mapping, moments for a trigger."""
	table = TRIGGER_INPUTS if trigger else SOURCE_INPUTS
	return list(table.get(_kind(source), ()))


def splitTarget(target):
	"""'particles.size' -> ('particles', 'size'); '' -> ('', '')."""
	target = str(target or '').strip()
	if '.' not in target:
		return '', target
	instrument, setting = target.split('.', 1)
	return instrument, setting


def joinTarget(instrument, setting):
	return '%s.%s' % (instrument, setting) if instrument and setting and setting != 'none' else ''


def instrumentsOf(known):
	"""The instruments in the target list, without hidden ones: INSTRUMENT_ORDER first, then the rest as found."""
	found = [name for name in INSTRUMENT_ORDER if any(splitTarget(t)[0] == name for t in known)]
	for target in known:
		instrument, setting = splitTarget(target)
		hidden = instrument in HIDDEN_INSTRUMENTS or setting in HIDDEN_SETTINGS or target in HIDDEN_TARGETS
		if instrument and not hidden and instrument not in found:
			found.append(instrument)
	return found


def settingsOf(instrument, known):
	"""An instrument's settings in the target list, in order, without hidden ones."""
	found = []
	for target in known:
		inst, setting = splitTarget(target)
		if inst == instrument and setting not in HIDDEN_SETTINGS and target not in HIDDEN_TARGETS:
			found.append(setting)
	return found


# ---------------------------------------------------------------- connections
# What students see: 4 connections per phase. Each one is Source + Input (the
# movement or moment), Instrument, and Does. The Input decides what Does
# offers:
#   a moment (hit, button, a note, enters a zone ...) -> one-time actions:
#       the instrument's own actions (Trigger Shape: pulse, spin ...; Media:
#       next file ...), or 'burst:<setting>' (the setting jumps by Amount and
#       falls back);
#   a movement (tilt, position, activity ...) -> 'set:<setting>' (the
#       movement controls the setting all the time).
# Some inputs are both (still, dancer present, in zone N): Does offers both.
# Connection N is stored as mapping slot N (continuous) or trigger slot N
# (moment), so presets, phases and show files keep their format. Slots 5-8
# are kept in the tables but not used.

NUM_CONNECTIONS = 4
CONNECTION_SOURCES = ('song', 'wearable1', 'wearable2', 'wearable3', 'body', 'camera', 'test')
MOMENT_ONLY = ('midi', 'hit', 'btn', 'sim_trigger')
MOMENT_TOO = ('still', 'pose_present', 'pose_zone1', 'pose_zone2', 'pose_zone3', 'pose_zone4', 'pose_zone5')
# One-time actions an instrument has besides a burst of a setting.
INSTRUMENT_ACTIONS = {
	'trigger': ('pulse', 'spin', 'sides', 'jump', 'flash'),
	'media': ('count:restartcount', 'count:nextcount', 'count:randomcount'),
	'tiles': ('count:shufflecount',),
}
# Settings a burst or a control never offers (menus, switches, counters).
NO_BURST = ('visible', 'preset', 'echo', 'source', 'playback', 'fit', 'orientation', 'edgeshape',
	'cycle', 'shuffle', 'matchends', 'randomdir', 'blackout', 'content', 'effect', 'strips', 'fade')
BURST_DEFAULT = 0.5  # of the setting's range
# Instruments whose connections offer only some settings (the rest stay on the Instruments tab).
CONNECTION_SETTINGS = {'tiles': ('opacity', 'scrollspeed', 'tilegap')}


def connectionInputs(source):
	"""Every input of a source for a connection: movements and moments, in menu order."""
	if source == 'song':
		return ['midi']
	names = sourceInputs(source) + [n for n in sourceInputs(source, trigger=True) if n not in sourceInputs(source)]
	return names


def inputKinds(name):
	"""('moment',), ('continuous',) or ('moment', 'continuous') for an input name."""
	if name in MOMENT_ONLY:
		return ('moment',)
	if name in MOMENT_TOO:
		return ('moment', 'continuous')
	return ('continuous',)


def doesOptions(instrument, kinds, settings):
	"""The Does values for an instrument and the input's kinds: actions, bursts, then controls."""
	found = []
	if instrument in CONNECTION_SETTINGS:
		settings = [s for s in settings if s in CONNECTION_SETTINGS[instrument]]
	if 'moment' in kinds:
		found += list(INSTRUMENT_ACTIONS.get(instrument, ()))
		found += ['burst:' + s for s in settings if s not in NO_BURST]
	if 'continuous' in kinds:
		found += ['set:' + s for s in settings if s not in ('preset',)]
	return found


def isContinuous(does):
	return str(does).startswith('set:')


def triggerAction(instrument, does):
	"""Connection Does -> the trigger row's does: 'pulse', 'burst:particles.size', 'count:media.nextcount'."""
	does = str(does)
	for prefix in ('burst:', 'count:'):
		if does.startswith(prefix):
			return '%s%s.%s' % (prefix, instrument, does[len(prefix):])
	return does


def connectionAction(action):
	"""Trigger row does -> (instrument, connection Does): the reverse of triggerAction."""
	action = str(action)
	for prefix in ('burst:', 'count:'):
		if action.startswith(prefix) and '.' in action:
			instrument, rest = action[len(prefix):].split('.', 1)
			return instrument, prefix + rest
	return 'trigger', action


def burstAmount(target, ranges=None):
	"""(default, slider low, slider high) of a burst's Amount: half the setting's range, either way."""
	low, high = targetRange(target, ranges)
	span = abs(high - low) or 1.0
	return round(span * BURST_DEFAULT, 4), -span, span


def connectionAmount(instrument, does, ranges=None):
	"""(default, low, high) of a connection's Amount, or None when Does has no amount (controls, counters)."""
	does = str(does)
	if does.startswith('burst:'):
		return burstAmount('%s.%s' % (instrument, does[len('burst:'):]), ranges)
	if does in INSTRUMENT_ACTIONS['trigger'] and instrument == 'trigger':
		return triggerAmount(does)
	return None
