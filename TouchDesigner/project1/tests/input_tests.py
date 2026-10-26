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
ADAPTER_ROWS = [
	['test/level', 'layer4.opacity', '', '', '', '', ''],
	['serial_accel', 'layer4.scale', '0', '1', '1', '3', ''],
	['serial_2', 'layer4.x', '', '', '', '', ''],
	['camera_motion', 'layer4.rotate', '0', '0.05', '0', '90', ''],
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
		inputs = op.Inputs
		inputs.op('osc_in').par.resetchannelspulse.pulse()
		for name in ('Simlevel', 'Simtrigger', 'Simzone', 'Simanimate', 'Oscenable', 'Serialenable'):
			inputs.par[name].val = 0
		inputs.par.Serialnames = ''
		inputs.par.Camerasource = 'off'
		inputs.op('osc_in').par.localaddress = ''
		inputs.op('serial_values').clear()

	def osc_on():
		op.Inputs.op('osc_in').par.localaddress = '127.0.0.1'
		op.Inputs.par.Oscenable = 1

	def osc_send():
		import socket
		import struct
		pad = lambda b: b + bytes(1) * (4 - len(b) % 4)
		packet = pad(b'/test/level') + pad(b',f') + struct.pack('>f', 0.6)
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.sendto(packet, ('127.0.0.1', int(op.Inputs.par.Oscport)))
		sock.close()

	def serial_line(line, names=''):
		def step():
			inputs = op.Inputs
			inputs.par.Serialenable = 1
			inputs.par.Serialnames = names
			inputs.op('serial_in_callbacks').module.onReceive(inputs.op('serial_in'), 0, line, b'')
		return base._do(step, 'serial line %r' % line)

	def camera_moving():
		v = base._live('layer4_rotate')
		check(s, 'camera test pattern -> motion', v > 1, 'layer4_rotate %.2f' % v)

	def no_errors():
		errs = op.Inputs.errors(recurse=True) + op.Engine.op('engine').scriptErrors()
		check(s, 'adapters: no errors without devices', not errs, errs)

	wait = base._do(lambda: None, 'wait')
	send = base._do(osc_send, 'osc send')  # UDP: send a few times, as a real sender would
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
		setRows(ADAPTER_ROWS), base._do(osc_on, 'osc on'), wait, wait,
		send, wait, send, wait, send, wait,
		base._expect(s, 'osc /test/level -> layer4 opacity', {'layer4_opacity': 0.6}),
		serial_line('accel=0.5'), base._expect(s, 'serial name=value', {'layer4_scale': 2}),
		serial_line('0.25 0.5', 'accel'), base._expect(s, 'serial plain numbers + names', {'layer4_scale': 1.5, 'layer4_x': 0.5}),
		serial_line('hello'), base._expect(s, 'serial bad line keeps values', {'layer4_scale': 1.5}),
		base._do(lambda: setattr(op.Inputs.par, 'Camerasource', 'test'), 'camera test'), wait, wait,
		base._do(camera_moving, 'camera moving'),
		base._do(lambda: setattr(op.Inputs.par, 'Camerasource', 'off'), 'camera off'), wait,
		base._expect(s, 'camera off -> motion 0', {'layer4_rotate': 0}),
		base._do(lambda: setattr(op.Inputs.par, 'Camerasource', 'camera'), 'camera, none attached'), wait, wait,
		base._do(no_errors, 'no errors'),
		base._do(reset, 'all inputs off'), wait,
		base._expect(s, 'inputs off -> base values', {'layer4_opacity': 1, 'layer4_scale': 1, 'layer4_x': 0, 'layer4_rotate': 0}),
		setRows(BAD_ROWS), wait, base._do(errors, 'input errors'),
		base._do(reset, 'sim defaults'),
	]
