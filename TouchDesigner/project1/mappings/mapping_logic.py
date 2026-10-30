"""Mapping page logic: dancer-friendly mappings -> input assignment rows.

Pure Python with no TouchDesigner imports, so it is unit-tested in plain
Python (tests/test_mapping_logic.py). The mappings component (MappingsExt)
holds 8 mapping slots and 4 presets (A-D) and uses this module to turn the
slots into rows for the engine, in the input assignment format:
  signal, target, in_min, in_max, out_min, out_max, smoothing

A slot names a movement signal and a visual target and gives the target's
From / To values. The signal's input range comes from the catalogue below,
so dancers never type sensor ranges; Sensitivity narrows it (2 = half the
movement reaches To).
"""

import re

NUM_SLOTS = 8
PRESETS = ('A', 'B', 'C', 'D')
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
TARGET_RANGES = {'scale': (0.5, 2.0), 'x': (-1.0, 1.0), 'y': (-1.0, 1.0), 'rotate': (0.0, 360.0),
	'content': (0.0, 6.0), 'effect': (0.0, 3.0)}
# Targets left out of the menu: switching presets from a movement would make
# the mappings change themselves.
HIDDEN_TARGETS = ('mapping.preset',)


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


def targetRange(target):
	"""(from, to) that covers a target's useful values, e.g. layer1.rotate -> (0, 360)."""
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
		slot = int(_number(cell('slot'), 0))
		if preset not in presets or not 1 <= slot <= NUM_SLOTS:
			continue
		values = presets[preset][slot - 1]
		for name in SLOT_FIELDS:
			text = cell(name)
			if text == '':
				continue
			values[name] = text if name in ('signal', 'target') else _number(text, SLOT_DEFAULTS[name])
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


def presetFromMidi(value):
	"""The preset a MIDI 'mapping.preset' value selects (1 = A ... 4 = D), or None for 0 / out of range."""
	index = int(round(value))
	return PRESETS[index - 1] if 1 <= index <= len(PRESETS) else None
