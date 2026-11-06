"""Engine: every frame, compute each visual value and publish it as a CHOP channel.

  value = the layer / master parameter (the starting look)
        -> MIDI assignments replayed up to the transport position (show_logic.evaluate)
        -> input assignments driven by live signals (show_logic.InputMapper):
           the input_assignments table, then the mapping page's rows
           (mappings/assignments), which win for the same target

Targets: the 4 layers, master, mapping.preset, and every instrument's settings
(any COMP in visuals with an 'Instrument' page, see show_logic). Instruments
are found again every frame, so a new one is a target at once.

The MIDI part is a pure function of the playback position, so pausing repeats
nothing and seeking or Reset restores the right state. Inputs keep working
while the music is paused.

Output: live_values (name, value) -> live CHOP, e.g. layer1_opacity, master_flash.
"""

NUM_LAYERS = 4
LAYER_PARS = {'visible': 'Visible', 'opacity': 'Opacity', 'red': 'Colorr', 'green': 'Colorg',
			  'blue': 'Colorb', 'scale': 'Scale', 'x': 'X', 'y': 'Y', 'rotate': 'Rotate',
			  'content': 'Content', 'effect': 'Effect'}
MASTER_PARS = {'level': 'Level', 'blackout': 'Blackout', 'flash': 'Flash'}

_midi = {'key': None, 'events': [], 'errors': []}
_inputs = {'key': None, 'assignments': [], 'errors': []}
MAPPING_ROW_OFFSET = 1000  # mapping page rows are numbered from here, apart from the table's rows
_mapper = None
_last_seconds = None


def onFrameStart(frame):
	global _mapper, _last_seconds
	sl = mod.show_logic
	found = instruments()
	ranges = _ranges(sl, found)
	known = sl.knownParams(NUM_LAYERS, ranges)
	_refreshMidi(sl, known)
	_refreshInputs(sl, known)
	state = sl.evaluate(_midi['events'], _base(sl, found, ranges), _transportSeconds())
	if _mapper is None:
		_mapper = sl.InputMapper()
	now = absTime.seconds
	dt = 0.0 if _last_seconds is None else max(0.0, now - _last_seconds)
	_last_seconds = now
	state = _mapper.apply(_inputs['assignments'], _signals(), state, dt)
	state['clock.seconds'] = _transportSeconds()
	_publish(state)


def instruments():
	"""[(COMP, [Par])]: every instrument in visuals and its target parameters, in page order."""
	visuals = getattr(op, 'Visuals', None)
	sl = op.Engine.op('show_logic').module
	if visuals is None:
		return []
	found = []
	for comp in visuals.children:
		if not comp.isCOMP:
			continue
		page = next((p for p in comp.customPages if p.name == sl.INSTRUMENT_PAGE), None)
		if page is not None:
			found.append((comp, [p for p in page.pars
				if p.style in sl.INSTRUMENT_STYLES and p.name not in sl.INSTRUMENT_SKIP]))
	return found


def targetRanges():
	"""{instrument target: (low, high)}, e.g. 'particles.energy': (0, 1). Read by the mapping page."""
	return _ranges(op.Engine.op('show_logic').module, instruments())


def knownTargets():
	"""Every target name (layers, master, controls, instruments). Read by the mapping page."""
	sl = op.Engine.op('show_logic').module
	return sl.knownParams(NUM_LAYERS, targetRanges())


def _ranges(sl, found):
	specs = []
	for comp, pars in found:
		specs.append((comp.name, [(p.name, p.style) + _sliderRange(p) for p in pars]))
	return sl.instrumentTargets(specs)


def _sliderRange(par):
	if par.isMenu:
		return (0.0, float(max(0, len(par.menuNames) - 1)))
	if par.isToggle:
		return (0.0, 1.0)
	return (float(par.normMin), float(par.normMax))


def _transportSeconds():
	transport = getattr(op, 'Transport', None)
	return float(transport.time.seconds) if transport else 0.0


def noteOns():
	"""((seconds, note) for every Note On in the MIDI file, cache key). Also read by midi_monitor."""
	transport = getattr(op, 'Transport', None)
	clip = transport.op('midiin_notes') if transport else None
	if clip is None or clip.numChans == 0:
		return [], None
	key = (str(transport.par.Midifile.eval()), clip.numSamples, clip.numChans)
	if key == _midi.get('notes_key'):
		return _midi['notes'], key
	gates = clip.numpyArray() > 0
	rate = clip.rate
	names = [c.name for c in clip.chans()]
	notes = []
	for c, name in enumerate(names):
		row = gates[c]
		starts = [0] if row[0] else []
		starts += [i for i in range(1, len(row)) if row[i] and not row[i - 1]]
		notes += [(i / rate, int(name[1:])) for i in starts]
	_midi['notes'], _midi['notes_key'] = notes, key
	return notes, key


def _refreshMidi(sl, known):
	table = op('midi_assignments')
	notes, notes_key = noteOns()
	key = (table.text, notes_key, tuple(known))
	if key == _midi['key']:
		return
	assignments, errors = sl.parseAssignments([[c.val for c in row] for row in table.rows()], known)
	_midi.update(key=key, events=sl.buildEvents(notes, assignments), errors=errors)
	_writeErrors()


def _refreshInputs(sl, known):
	table = op('input_assignments')
	mappings = getattr(op, 'Mappings', None)
	mapped = mappings.op('assignments') if mappings else None
	key = (table.text, mapped.text if mapped is not None else '', tuple(known))
	if key == _inputs['key']:
		return
	assignments, errors = sl.parseInputAssignments([[c.val for c in row] for row in table.rows()], known)
	if mapped is not None:
		more, more_errors = sl.parseInputAssignments([[c.val for c in row] for row in mapped.rows()], known)
		for a in more:
			a.row += MAPPING_ROW_OFFSET
		assignments += more
		errors += ['mapping page: ' + e for e in more_errors]
	_inputs.update(key=key, assignments=assignments, errors=errors)
	_writeErrors()


def _writeErrors():
	out = op('assignment_errors')
	out.clear(keepFirstRow=True)
	for e in _midi['errors']:
		out.appendRow(['midi_assignments', e])
	for e in _inputs['errors']:
		out.appendRow(['input_assignments', e])


def _base(sl, found=None, ranges=None):
	"""Starting values read from the layer, master and instrument parameters (the manual settings)."""
	if found is None:
		found = instruments()
		ranges = _ranges(sl, found)
	base = sl.defaultBase(NUM_LAYERS)
	visuals = getattr(op, 'Visuals', None)
	if visuals is None:
		return base
	for i in range(1, NUM_LAYERS + 1):
		layer = visuals.op('layer%d' % i)
		if layer is not None:
			for name, par_name in LAYER_PARS.items():
				_read(base, 'layer%d.%s' % (i, name), layer.par[par_name])
	for name, par_name in MASTER_PARS.items():
		_read(base, 'master.' + name, visuals.par[par_name])
	for comp, pars in found:
		for par in pars:
			key = '%s.%s' % (comp.name.lower(), par.name.lower())
			if key in ranges:
				_read(base, key, par)
	return base


def _read(base, key, par):
	if par is None:
		return
	base[key] = float(par.menuIndex if par.isMenu else par.eval())


def _signals():
	inputs = getattr(op, 'Inputs', None)
	chop = inputs.op('signals') if inputs else None
	if chop is None:
		return {}
	return {c.name: c.eval() for c in chop.chans()}


def _publish(state):
	out = op('live_values')
	names = sorted(state)
	if out.numRows != len(names) or out[0, 0] is None or out[0, 0].val != names[0].replace('.', '_'):
		out.clear()
		for name in names:
			out.appendRow([name.replace('.', '_'), '%g' % state[name]])
		return
	for r, name in enumerate(names):
		text = '%g' % state[name]
		if out[r, 1].val != text:
			out[r, 1] = text
