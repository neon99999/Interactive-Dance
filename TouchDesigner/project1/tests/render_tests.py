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

	def four_layer_setup():
		resetLayers()
		look = {1: dict(Colorr=1, Colorg=0, Colorb=0, X=-0.5),
				2: dict(Colorr=0, Colorg=1, Colorb=0, X=0.5, Content='square'),
				3: dict(Colorr=0, Colorg=0, Colorb=1),
				4: dict(Opacity=0.5, Scale=0.5)}
		for i, pars in look.items():
			layer = op.Visuals.op('layer%d' % i)
			for name, value in pars.items():
				setattr(layer.par, name, value)

	def master(**pars):
		def step():
			for name, value in pars.items():
				setattr(op.Visuals.par, name, value)
		return base._do(step, 'master %s' % pars)

	four_rows = [['60', 'layer1', 'show', '', ''], ['60', 'layer2', 'show', '', ''],
				 ['62', 'layer3', 'show', '', ''], ['64', 'layer4', 'show', '', '']]
	four = [
		base._do(four_layer_setup, 'four layer setup'), base._setRows(four_rows),
		base._seek(11.0), expect('layer1 red circle left', 320, 360, [1, 0, 0]),
		expect('layer2 green square right', 960, 360, [0, 1, 0]),
		expect('layer3 blue centre, layer4 still hidden', 640, 360, [0, 0, 1]),
		base._seek(16.0), expect('layer4 (white 50%) composited over layer3', 640, 360, [0.5, 0.5, 1]),
		expect('outside small layer4 only layer3', 760, 360, [0, 0, 1]),
		master(Level=0.5), expect('master level 0.5 halves output', 320, 360, [0.5, 0, 0]),
		master(Level=1, Blackout=1), expect('blackout', 960, 360, [0, 0, 0]),
		master(Blackout=0), base._do(resetLayers, 'reset layers'),
	]

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
	] + four


def resetLayers():
	"""Put every layer and the master controls back to their defaults."""
	for i in range(1, 5):
		layer = op.Visuals.op('layer%d' % i)
		if layer is None:
			continue
		for p in layer.customPars:
			if p.name in ('Visible', 'Opacity', 'Colorr', 'Colorg', 'Colorb', 'Scale', 'X', 'Y', 'Rotate',
						  'Content', 'Effect'):
				p.val = p.default
	op.Visuals.par.Level = 1
	op.Visuals.par.Blackout = 0
	op.Visuals.par.Flash = 0
