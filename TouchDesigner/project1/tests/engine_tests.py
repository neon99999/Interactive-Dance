"""In-TouchDesigner integration tests for the toolkit.

Run from the Textport:  op('/project1/tests/engine_tests').module.Run()
Each step runs a few frames after the previous one so the engine and the
renders have cooked. Results land in tests/results (suite, check, PASS/FAIL).
Assignment tables are backed up and restored around the tests.
"""

STEP_FRAMES = 3
TOL = 1e-3

TEST_ROWS = [
	['60', 'layer1', 'show', '', ''],
	['62', 'layer1.scale', 'set', '2', ''],
	['64', 'layer1', 'toggle', '', ''],
	['65', 'master.flash', 'trigger', '1', '0.5'],
	['67', 'layer1.opacity', 'fade', '0', '2'],
	['65', 'layer1.x', 'set', '0.25', ''],
	['67', 'layer1.x', 'set', '-0.25', ''],
]

_queue = []
_backup = {}


def Run():
	results = op('results')
	results.clear(keepFirstRow=True)
	_queue[:] = _engineSteps() + _invalidConfigSteps() + _extraSteps()
	_queue.append(_finish)
	_backupTables()
	_next()


def _extraSteps():
	"""Hook for later suites (render, inputs). Returns a list of steps."""
	extra = me.parent().op('render_tests')
	return extra.module.Steps(_check) if extra is not None else []


def _next():
	if not _queue:
		return
	step = _queue.pop(0)
	try:
		step()
	except Exception as e:
		_check('harness', getattr(step, '__name__', 'step'), False, 'raised %r' % e)
	run(_next, delayFrames=STEP_FRAMES)


def _check(suite, name, ok, detail=''):
	op('results').appendRow([suite, name, 'PASS' if ok else 'FAIL', detail])


def _live(name):
	chan = op.Engine.op('live')[name]
	return None if chan is None else float(chan.eval())


def _expect(suite, label, expected):
	def step():
		got = {k: _live(k) for k in expected}
		bad = {k: (got[k], v) for k, v in expected.items() if got[k] is None or abs(got[k] - v) > TOL}
		_check(suite, label, not bad, 'got/expected %s' % bad if bad else str(got))
	step.__name__ = label
	return step


def _do(fn, label):
	fn.__name__ = label
	return fn


def _seek(seconds):
	def step():
		t = op.Transport
		t.par.Seekto = seconds
		t.par.Seek.pulse()
	return _do(step, 'seek %s' % seconds)


def _setRows(rows):
	def step():
		table = op.Engine.op('midi_assignments')
		table.clear(keepFirstRow=True)
		for row in rows:
			table.appendRow(row)
		for _ in range(16 - len(rows)):
			table.appendRow([''] * 5)
	return _do(step, 'set rows')


def _engineSteps():
	s = 'engine'
	pause = _do(lambda: setattr(op.Transport.par, 'Play', 0), 'pause')
	reset = _do(lambda: op.Transport.par.Reset.pulse(), 'reset')
	return [
		pause, _setRows(TEST_ROWS),
		_seek(4.0), _expect(s, 'before first note', {'layer1_visible': 0, 'layer1_scale': 1, 'master_flash': 0}),
		_seek(5.5), _expect(s, 'show at 5s', {'layer1_visible': 1, 'layer1_scale': 1}),
		_seek(12.0), _expect(s, 'set value at 10s', {'layer1_visible': 1, 'layer1_scale': 2}),
		_seek(16.0), _expect(s, 'toggle at 15s', {'layer1_visible': 0, 'layer1_scale': 2}),
		_seek(20.2), _expect(s, 'chord: trigger + fade + conflict', {'master_flash': 1, 'layer1_opacity': 0.9, 'layer1_x': -0.25}),
		_expect(s, 'paused: state unchanged', {'master_flash': 1, 'layer1_opacity': 0.9}),
		_seek(20.6), _expect(s, 'trigger expired, fade continues', {'master_flash': 0, 'layer1_opacity': 0.7}),
		_seek(25.0), _expect(s, 'fade finished', {'layer1_opacity': 0, 'master_flash': 0}),
		_seek(11.0), _expect(s, 'seek backward restores', {'layer1_visible': 1, 'layer1_scale': 2, 'layer1_opacity': 1, 'layer1_x': 0}),
		reset, _expect(s, 'reset restores start', {'layer1_visible': 0, 'layer1_scale': 1, 'layer1_opacity': 1, 'layer1_x': 0}),
		_seek(25.0), _expect(s, 'repeat: same end state', {'layer1_visible': 0, 'layer1_scale': 2, 'layer1_opacity': 0, 'layer1_x': -0.25}),
		_seek(20.3), _expect(s, 'seek into trigger window', {'master_flash': 1}),
	]


def _invalidConfigSteps():
	s = 'config'
	bad = [['abc', 'layer1', 'show', '', ''], ['60', 'layer9', 'show', '', ''],
		   ['60', 'layer1', 'jump', '', ''], ['60', 'layer1.opacity', 'fade', '', '1'],
		   ['60', 'layer1', 'show', '', '']]

	def check_errors():
		errors = op.Engine.op('assignment_errors')
		n = errors.numRows - 1
		_check(s, 'invalid rows reported', n == 4, '%d errors' % n)
		_check(s, 'engine still running', not op.Engine.op('engine').scriptErrors(), op.Engine.op('engine').scriptErrors())

	return [_setRows(bad), _seek(6.0), _do(check_errors, 'check errors'),
			_expect(s, 'valid row still applies', {'layer1_visible': 1})]


def _backupTables():
	for name in ('midi_assignments', 'input_assignments'):
		table = op.Engine.op(name)
		_backup[name] = [[c.val for c in row] for row in table.rows()]


def _finish():
	for name, rows in _backup.items():
		table = op.Engine.op(name)
		table.clear()
		for row in rows:
			table.appendRow(row)
	op.Transport.par.Reset.pulse()
	results = op('results')
	fails = sum(1 for r in range(1, results.numRows) if results[r, 2].val != 'PASS')
	_check('summary', '%d checks' % (results.numRows - 1), fails == 0, '%d failed' % fails)
