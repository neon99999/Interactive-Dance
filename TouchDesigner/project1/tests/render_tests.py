"""Render tests: drive the visuals through MIDI assignments and read output pixels.

Called by engine_tests.Run() through Steps(check). Pixels are read from
visuals/null_out with numpyArray (row 0 is the bottom of the image).
"""

ROWS = [
	['60', 'layer1', 'show', '', ''],
	['60', 'layer1.red', 'set', '1', ''],
	['60', 'layer1.green', 'set', '0', ''],
	['60', 'layer1.blue', 'set', '0', ''],
	['62', 'layer1.x', 'set', '0.5', ''],
	['64', 'layer1.opacity', 'fade', '0', '2'],
	['65', 'master.flash', 'trigger', '1', '0.5'],
	['67', 'layer1', 'hide', '', ''],
]
TOL = 0.06


def Steps(check):
	base = me.parent().op('engine_tests').module
	s = 'render'

	def pixel(x, y):
		img = op.Visuals.op('null_out').numpyArray()
		return [round(float(c), 3) for c in img[y, x, :3]]

	def expect(label, x, y, rgb):
		def step():
			got = pixel(x, y)
			ok = all(abs(g - e) <= TOL for g, e in zip(got, rgb))
			check(s, label, ok, 'pixel (%d,%d) got %s expected %s' % (x, y, got, rgb))
		return base._do(step, label)

	def layer_defaults():
		layer = op.Visuals.op('layer1')
		layer.par.Visible = 0; layer.par.Opacity = 1; layer.par.Scale = 1
		layer.par.X = 0; layer.par.Y = 0; layer.par.Content = 'circle'
		layer.par.Colorr = layer.par.Colorg = layer.par.Colorb = 1
		op.Visuals.par.Level = 1; op.Visuals.par.Blackout = 0

	return [
		base._do(layer_defaults, 'layer defaults'), base._setRows(ROWS),
		base._seek(4.0), expect('hidden before show', 640, 360, [0, 0, 0]),
		base._seek(6.0), expect('show + set colour red', 640, 360, [1, 0, 0]),
		base._seek(11.0), expect('set x moves shape right', 960, 360, [1, 0, 0]),
		expect('old position now empty', 640, 360, [0, 0, 0]),
		base._seek(16.0), expect('fade half way (opacity 0.5)', 960, 360, [0.5, 0, 0]),
		base._seek(20.2), expect('flash trigger whites out', 100, 100, [1, 1, 1]),
		base._seek(21.0), expect('hide after flash', 960, 360, [0, 0, 0]),
		base._seek(6.0), expect('seek back restores red shape', 640, 360, [1, 0, 0]),
	]
