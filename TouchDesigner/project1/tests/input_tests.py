"""Input tests: simulated movement signals driving visuals through input_assignments.

Called by engine_tests.Run() through Steps(check). Music stays paused the whole
time, so every change seen here comes from the inputs, not the MIDI timeline.
"""

ROWS = [
	['sim_level', 'layer1.opacity', '0', '1', '0.2', '0.8', ''],
	['sim_trigger', 'master.flash', '', '', '', '', ''],
	['sim_zone', 'layer2', '', '', '', '', ''],
	['sim_level', 'layer1.scale', '0', '1', '1', '2', '0.5'],
	['no_such_signal', 'layer1.rotate', '', '', '', '', ''],
	['sim_level', 'layer3.x', '0.5', '1', '1', '-1', ''],
]
BAD_ROWS = [
	['sim_level', 'layer9.opacity', '', '', '', '', ''],
	['sim_level', 'layer1.opacity', '0.5', '0.5', '', '', ''],
	['', 'layer1.opacity', '', '', '', '', ''],
	['sim_level', 'layer1.opacity', 'low', '', '', '', ''],
]


def Steps(check):
	base = me.parent().op('engine_tests').module
	s = 'inputs'
	clock = {}

	def setRows(rows):
		def step():
			table = op.Engine.op('input_assignments')
			table.clear(keepFirstRow=True)
			for row in rows:
				table.appendRow(row)
			for _ in range(8 - len(rows)):
				table.appendRow([''] * 7)
		return base._do(step, 'set input rows')

	def sim(**values):
		def step():
			for name, value in values.items():
				op.Inputs.par[name].val = value
		return base._do(step, 'sim %s' % values)

	def start():
		op.Transport.par.Play = 0
		op.Transport.par.Seekto = 3.0
		op.Transport.par.Seek.pulse()
		op.Engine.op('midi_assignments').clear(keepFirstRow=True)

	def note_clock():
		clock['t'] = base._live('clock_seconds')

	def smoothing_partial():
		v = base._live('layer1_scale')
		check(s, 'smoothing: moving, not jumped', 1.05 < v < 1.95, 'layer1_scale %.3f' % v)

	def clock_still():
		t = base._live('clock_seconds')
		check(s, 'music stayed paused', abs(t - clock['t']) < 1e-6, '%.3f -> %.3f' % (clock['t'], t))

	def errors():
		table = op.Engine.op('assignment_errors')
		rows = [table[r, 1].val for r in range(1, table.numRows) if table[r, 0].val == 'input_assignments']
		check(s, 'invalid input rows reported', len(rows) == 4, '; '.join(rows))
		check(s, 'engine still running', not op.Engine.op('engine').scriptErrors(), op.Engine.op('engine').scriptErrors())

	def reset():
		for name in ('Simlevel', 'Simtrigger', 'Simzone', 'Simanimate'):
			op.Inputs.par[name].val = 0

	wait = base._do(lambda: None, 'wait')
	return [
		base._do(start, 'pause at 3s'), base._do(reset, 'sim defaults'), setRows(ROWS), wait,
		base._do(note_clock, 'note clock'),
		base._expect(s, 'level 0: range mapped', {'layer1_opacity': 0.2, 'layer1_scale': 1, 'layer3_x': 1}),
		base._expect(s, 'missing signal keeps base value', {'layer1_rotate': 0}),
		sim(Simlevel=0.5), base._expect(s, 'level 0.5', {'layer1_opacity': 0.5, 'layer3_x': 1}),
		sim(Simlevel=1.0), base._do(smoothing_partial, 'smoothing partial'),
		base._expect(s, 'level 1: range + inverted range', {'layer1_opacity': 0.8, 'layer3_x': -1}),
		sim(Simtrigger=1), base._expect(s, 'trigger held -> flash', {'master_flash': 1}),
		sim(Simtrigger=0), base._expect(s, 'trigger released', {'master_flash': 0}),
		sim(Simzone=1), base._expect(s, 'zone on -> layer2 visible', {'layer2_visible': 1}),
		sim(Simzone=0), base._expect(s, 'zone off -> layer2 hidden', {'layer2_visible': 0}),
		base._do(clock_still, 'clock still'),
		setRows(BAD_ROWS), wait, base._do(errors, 'input errors'),
		base._do(reset, 'sim defaults'),
	]
