"""Phases: the piece in up to 10 phases; each phase keeps its own settings.

Pure Python with no TouchDesigner imports, so it is unit-tested in plain
Python (tests/test_phases.py). PhasesExt (the phases component) is the
TouchDesigner side.

A phase is one part of the song. Each phase keeps a snapshot of the
settings a student changes: every instrument's settings and the mappings
(the mappings keep their own per-phase store, see mapping_logic). When the
phase changes, its snapshot is put back; a phase with no snapshot yet
starts as a copy of the settings on screen.

A phase starts from a MIDI note of the song (Note for This Phase, Follow
MIDI on), from the Phase menu, or from the number keys: 1-9 select phases
1-9 and 0 selects phase 10.
"""

NUM_PHASES = 10
SNAPSHOT_COLUMNS = ('phase', 'comp', 'par', 'value')


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


def keyPhase(key):
	"""The phase a number key selects ('1' -> 1 ... '9' -> 9, '0' -> 10), or None for any other key."""
	key = str(key).strip()
	if len(key) != 1 or not key.isdigit():
		return None
	phase = int(key) or 10
	return phase if phase <= NUM_PHASES else None


def readSnapshots(rows):
	"""Snapshot table rows (header first) -> {phase: {comp: {par: value text}}}.

	Phases with no rows are left out: they have no snapshot yet.
	"""
	snaps = {}
	header = [str(c).strip().lower() for c in rows[0]] if rows else []
	if not all(name in header for name in SNAPSHOT_COLUMNS):
		return snaps
	col = {name: header.index(name) for name in SNAPSHOT_COLUMNS}
	for row in rows[1:]:
		if len(row) <= max(col.values()):
			continue
		try:
			phase = int(float(str(row[col['phase']])))
		except ValueError:
			continue
		if not 1 <= phase <= NUM_PHASES:
			continue
		comp, par = str(row[col['comp']]).strip(), str(row[col['par']]).strip()
		if comp and par:
			snaps.setdefault(phase, {}).setdefault(comp, {})[par] = str(row[col['value']])
	return snaps


def snapshotRows(snaps):
	"""{phase: {comp: {par: value}}} -> table rows (header first), in phase, comp, par order."""
	rows = [list(SNAPSHOT_COLUMNS)]
	for phase in sorted(p for p in snaps if 1 <= p <= NUM_PHASES):
		for comp in sorted(snaps[phase]):
			for par in sorted(snaps[phase][comp]):
				rows.append([str(phase), comp, par, valueText(snaps[phase][comp][par])])
	return rows


def valueText(value):
	"""One stored form for a setting's value: text as it is, numbers without trailing zeros."""
	if isinstance(value, bool):
		return '1' if value else '0'
	if isinstance(value, (int, float)):
		return '%.6g' % value
	return str(value)


def changedSettings(current, stored):
	"""{comp: {par: value}} of the settings in current that differ from stored (compared as text)."""
	changed = {}
	for comp, pars in current.items():
		old = stored.get(comp, {})
		for par, value in pars.items():
			if valueText(value) != valueText(old.get(par, None)) or par not in old:
				changed.setdefault(comp, {})[par] = value
	return changed
