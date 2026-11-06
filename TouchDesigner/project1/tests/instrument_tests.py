"""Instrument tests (Stage E): MIDI, mappings, presets and the compositor with the visual instruments.

Called by engine_tests.Run() through Steps(check), after the mapping tests.
The harness backs up and restores the instruments' settings, the MIDI rows
and the mapping page. Test MIDI notes (media/test/sync_test.mid): 60 at 5 s,
62 at 10 s, 64 at 15 s, 65 at 20 s.
"""

MIDI_ROWS = [
	['60', 'particles.colour', 'set', '2', ''],     # 5 s: Ember
	['62', 'video', 'show', '', ''],                # 10 s
	['62', 'video.opacity', 'fade', '0.2', '2'],    # 10-12 s
	['64', 'particles.energy', 'set', '0.9', ''],   # 15 s
	['65', 'particles', 'hide', '', ''],            # 20 s
]


def Steps(check):
	base = me.parent().op('engine_tests').module
	s = 'instruments'
	wait = base._do(lambda: None, 'wait')
	visuals = op.Visuals

	def inst(name):
		return visuals.op(name)

	def start():
		op.Transport.par.Play = 0
		particles, video, shapes = inst('particles'), inst('video'), inst('shapes')
		particles.par.Visible = 1
		particles.par.Preset = 'flowing'
		particles.par.Reset.pulse()
		video.par.Visible = 0
		video.par.Opacity = 1
		video.par.Source = 'test'
		shapes.par.Visible = 0
		_mappings({})

	def _mappings(slots):
		"""Write mapping preset A with the given {slot index: slot} and load it."""
		mappings = op.Mappings
		logic = mappings.op('mapping_logic').module
		presets = {p: logic.emptySlots() for p in logic.PRESETS}
		for index, slot in slots.items():
			presets['A'][index] = slot
		mappings.ext.Mappings._writePresets(presets)
		mappings.par.Followmidi = 0
		mappings.par.Preset = 'A'
		mappings.LoadPreset('A')

	def slot(signal, target, low, high):
		return {'on': 1.0, 'signal': signal, 'target': target, 'from': float(low), 'to': float(high), 'smooth': 0.0, 'sens': 1.0}

	def compositor_has(label, names):
		def step():
			got = [o.parent().name for o, _, _ in visuals.op('compositor').module.layers()]
			check(s, label, got == names, str(got))
		return base._do(step, label)

	def par_is(label, path, par, expected, tol=1e-3):
		def step():
			got = float(op(path).par[par].eval())
			check(s, label, abs(got - expected) <= tol, 'got %.4f expected %.4f' % (got, expected))
		return base._do(step, label)

	def setp(name, par, value):
		return base._do(lambda: setattr(inst(name).par, par, value), '%s.%s = %s' % (name, par, value))

	def pulse(name, par):
		return base._do(lambda: inst(name).par[par].pulse(), '%s.%s pulse' % (name, par))

	def pars_are(label, name, expected):
		def step():
			comp = inst(name)
			bad = {}
			for par, value in expected.items():
				got = comp.par[par].eval()
				if isinstance(value, str) and got != value or not isinstance(value, str) and abs(float(got) - value) > 1e-3:
					bad[par] = (got, value)
			check(s, label, not bad, 'got/expected %s' % bad if bad else 'ok')
		return base._do(step, label)

	midi = [
		base._do(start, 'instruments start'), wait, base._setRows(MIDI_ROWS),
		base._seek(4.0), wait, wait,
		base._expect(s, 'before the notes: manual values', {'particles_colour': 0, 'particles_energy': 0.4, 'video_visible': 0}),
		compositor_has('compositor: particles only', ['particles']),
		base._seek(5.5), wait, wait,
		base._expect(s, 'MIDI set particles.colour', {'particles_colour': 2}),
		base._seek(12.5), wait, wait,
		base._expect(s, 'MIDI show video + opacity fade', {'video_visible': 1, 'video_opacity': 0.2}),
		compositor_has('compositor: video under particles', ['video', 'particles']),
		par_is('fade reaches the compositor', '/project1/visuals/level_slot1', 'opacity', 0.2),
		base._seek(16.0), wait, wait,
		base._expect(s, 'MIDI set particles.energy', {'particles_energy': 0.9}),
		par_is('energy reaches the particles (curl amp)', '/project1/visuals/particles/geo/force_curl', 'amp0', 0.15 + 0.9 * 1.6),
		setp('particles', 'Energy', 0.1), wait, wait,
		base._expect(s, 'after a MIDI set the slider waits (documented rule)', {'particles_energy': 0.9}),
		base._seek(20.5), wait, wait,
		base._expect(s, 'MIDI hide particles', {'particles_visible': 0}),
		compositor_has('compositor: particles gone', ['video']),
		base._seek(4.0), wait, wait,
		base._expect(s, 'seek back: manual values again', {'particles_colour': 0, 'particles_energy': 0.1, 'video_visible': 0, 'particles_visible': 1}),
		base._setRows([]), wait,
	]

	mapping = [
		base._do(lambda: setattr(op.Inputs.par, 'Simlevel', 0.5), 'Simlevel 0.5'),
		base._do(lambda: _mappings({0: slot('sim_level', 'particles.turbulence', 0, 1),
									  1: slot('sim_level', 'video.opacity', 0, 1)}), 'map sim_level'),
		setp('video', 'Visible', 1), wait, wait, wait,
		base._expect(s, 'mapping drives particles.turbulence', {'particles_turbulence': 0.5}),
		base._expect(s, 'mapping drives video.opacity', {'video_opacity': 0.5}),
		par_is('mapped opacity reaches the compositor', '/project1/visuals/level_slot1', 'opacity', 0.5),
		base._do(lambda: setattr(op.Inputs.par, 'Simlevel', 0.8), 'Simlevel 0.8'), wait, wait, wait,
		base._expect(s, 'mapping follows the signal', {'particles_turbulence': 0.8}),
		base._do(lambda: setattr(op.Mappings.par, 'Map1on', 0), 'slot 1 off'), wait, wait, wait,
		base._expect(s, 'mapping off: manual turbulence back', {'particles_turbulence': 0.45, 'video_opacity': 0.8}),
		base._do(lambda: _mappings({}), 'mappings empty'), wait, wait,
		base._expect(s, 'all mappings off: manual opacity back', {'video_opacity': 1}),
	]

	presets = [
		setp('particles', 'Preset', 'calm'), wait,
		pars_are('particles preset calm', 'particles', {'Energy': 0.15, 'Spread': 0.75, 'Trails': 0.85, 'Colour': 'ocean'}),
		setp('particles', 'Energy', 0.7), wait, pulse('particles', 'Reset'), wait,
		pars_are('particles Reset restores the preset', 'particles', {'Energy': 0.15}),
		setp('video', 'Preset', 'abstract'), wait,
		pars_are('video preset abstract', 'video', {'Feedback': 0.95, 'Zoom': 0.4, 'Mix': 1}),
		pars_are('presets leave the compositor settings alone', 'video', {'Opacity': 1, 'Blend': 'normal', 'Order': 1}),
		setp('video', 'Visible', 0), wait,
		setp('noise', 'Preset', 'lava'), wait,
		pars_are('noise preset lava', 'noise', {'Scale': 0.4, 'Warp': 0.7, 'Colour': 'lava'}),
		setp('noise', 'Visible', 1), wait, wait,
		compositor_has('compositor: noise under particles', ['noise', 'particles']),
		setp('noise', 'Visible', 0), wait, wait,
		compositor_has('compositor: noise off again', ['particles']),
	]

	def panel(mode, instrument):
		def step():
			control = op.Control
			control.par.Mode = mode
			control.par.Instrument = instrument
			control.Rebuild()
		return base._do(step, 'panel %s %s' % (mode, instrument))

	def panel_pages():
		control = op.Control
		names = [p.name for p in control.customPages if p.name != 'About']
		check(s, 'panel: five tabs (plus Embody About)', names == ['Show', 'Instruments', 'Composition', 'Movement', 'Inputs'], ', '.join(names))
		basic = len(control.customPars)
		control.par.Mode = 'advanced'
		control.Rebuild()
		check(s, 'panel: Advanced shows more than Basic', len(control.customPars) > basic, '%d -> %d' % (basic, len(control.customPars)))
		control.par.Mode = 'basic'
		control.Rebuild()

	def panel_binds():
		control = op.Control
		particles = inst('particles')
		control.par.Instparticlesenergy = 0.66
		forward = float(particles.par.Energy.eval())
		particles.par.Energy = 0.33
		back = float(control.par.Instparticlesenergy.eval())
		check(s, 'panel slider <-> instrument parameter (both ways)', abs(forward - 0.66) < 1e-4 and abs(back - 0.33) < 1e-4, '%.2f, %.2f' % (forward, back))
		control.par.Compnoisevisible = 1
		check(s, 'panel Composition On -> noise Visible', int(inst('noise').par.Visible.eval()) == 1, '')
		control.par.Compnoisevisible = 0

	panel_steps = [
		panel('basic', 'particles'), wait, base._do(panel_pages, 'panel pages'),
		base._do(panel_binds, 'panel binds'), wait,
		setp('particles', 'Preset', 'calm'), wait, setp('particles', 'Energy', 0.9), wait,
		base._do(lambda: op.Control.par.Instparticlesreset.pulse(), 'panel Reset pulse'), wait, wait,
		pars_are('panel Reset reaches the instrument', 'particles', {'Energy': 0.15}),
	]

	return midi + mapping + presets + panel_steps
