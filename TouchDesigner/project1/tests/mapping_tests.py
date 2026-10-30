"""Mapping tests: the mapping page drives visuals, MIDI switches presets, the language switch.

Called by engine_tests.Run() through Steps(check), after the input tests. The
harness (engine_tests) backs up and restores the mapping presets, the
Preset and Follow MIDI settings and the language.
"""

MIDI_ROWS = [
	['60', 'mapping.preset', 'set', '2', ''],  # 5 s: preset B
	['62', 'mapping.preset', 'set', '1', ''],  # 10 s: back to A
]

def Steps(check):
	base = me.parent().op('engine_tests').module
	s = 'mappings'

	def slot(signal, target, low, high):
		return {'on': 1.0, 'signal': signal, 'target': target, 'from': float(low), 'to': float(high), 'smooth': 0.0, 'sens': 1.0}

	def start():
		mappings = op.Mappings
		op.Transport.par.Play = 0
		logic = mappings.op('mapping_logic').module
		presets = {p: logic.emptySlots() for p in logic.PRESETS}
		presets['A'][0] = slot('sim_level', 'layer1.opacity', 0.2, 0.8)
		presets['B'][0] = slot('sim_level', 'layer1.scale', 1, 3)
		mappings.ext.Mappings._writePresets(presets)
		mappings.par.Followmidi = 1
		mappings.par.Preset = 'A'
		mappings.LoadPreset('A')
		op.Inputs.par.Simlevel = 0.5

	def preset_is(name):
		def step():
			got = op.Mappings.par.Preset.eval()
			check(s, 'preset %s selected' % name, got == name, got)
		return base._do(step, 'preset is %s' % name)

	def set_par(name, value):
		return base._do(lambda: setattr(op.Mappings.par, name, value), '%s = %s' % (name, value))

	def new_slot():
		mappings = op.Mappings
		mappings.par.Map2signal = 'sim_level'
		mappings.par.Map2target = 'layer2.x'
		mappings.par.Map2on = 1

	def slot_range():
		got = (op.Mappings.par.Map2from.eval(), op.Mappings.par.Map2to.eval())
		check(s, 'new visual -> its natural From / To', got == (-1.0, 1.0), str(got))
		rows = [r[1].val for r in op.Mappings.op('assignments').rows()[1:]]
		check(s, 'slot written to the assignments table', 'layer2.x' in rows, str(rows))

	def spanish():
		label = op.Mappings.par.Followmidi.label
		expected = op.Lang.T('mappings.Followmidi.label')
		menu = op.Mappings.par.Map1signal.menuLabels
		names = op.Mappings.par.Map1signal.menuNames
		pose = menu[names.index('pose_hand_l')] if 'pose_hand_l' in names else ''
		check(s, 'Spanish labels', label == expected and label == 'Seguir MIDI', label)
		check(s, 'Spanish menu labels', pose == op.Lang.T('signal.pose_hand_l') and pose.startswith('Cuerpo'), pose)

	def english():
		label = op.Mappings.par.Followmidi.label
		check(s, 'English labels back', label == 'Follow MIDI' and op.Lang.par['Language'].eval() == 'en', label)

	def pose_monitor():
		monitor = op('/project1/pose_monitor')
		values = monitor.op('panel_values')
		ok = monitor.errors(recurse=True) == '' and values.numChans == 12 + 3 * 33
		check(s, 'pose monitor: no errors, all values', ok, '%d channels %s' % (values.numChans, monitor.errors(recurse=True)))

	def clear_midi():
		op.Engine.op('midi_assignments').clear(keepFirstRow=True)

	wait = base._do(lambda: None, 'wait')
	return [
		base._do(start, 'mappings start'), base._setRows(MIDI_ROWS), base._seek(4.0), wait, wait,
		base._expect(s, 'preset A maps level -> opacity', {'mapping_preset': 0, 'layer1_opacity': 0.5, 'layer1_scale': 1}),
		base._seek(5.5), wait, wait, wait,
		preset_is('B'),
		base._expect(s, 'MIDI note -> preset B', {'mapping_preset': 2, 'layer1_scale': 2, 'layer1_opacity': 1}),
		base._seek(12.0), wait, wait, wait,
		preset_is('A'),
		base._expect(s, 'later note -> back to A', {'mapping_preset': 1, 'layer1_opacity': 0.5, 'layer1_scale': 1}),
		set_par('Followmidi', 0), base._seek(5.5), wait, wait, wait,
		preset_is('A'),
		set_par('Followmidi', 1), base._seek(12.0), wait,
		base._do(new_slot, 'new slot'), wait, wait, wait,
		base._do(slot_range, 'slot range'),
		base._expect(s, 'new slot drives the visual', {'layer2_x': 0}),
		set_par('Preset', 'B'), wait, wait, wait,
		base._expect(s, 'Preset menu -> B', {'layer1_scale': 2, 'layer2_x': 0}),
		base._do(lambda: setattr(op.Lang.par, 'Language', 'es'), 'Spanish'), wait, wait,
		base._do(spanish, 'Spanish check'),
		base._do(lambda: setattr(op.Lang.par, 'Language', 'en'), 'English'), wait, wait,
		base._do(english, 'English check'),
		base._do(pose_monitor, 'pose monitor'),
		base._do(clear_midi, 'clear MIDI rows'), base._seek(3.0), wait, wait,
	]
