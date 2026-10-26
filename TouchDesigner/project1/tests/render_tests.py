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

	def layer1(**pars):
		def step():
			layer = op.Visuals.op('layer1')
			for name, value in pars.items():
				setattr(layer.par, name, value)
		return base._do(step, 'layer1 %s' % pars)

	def expect_changes(label):
		"""The image must differ between two reads a few frames apart (animated content)."""
		seen = []

		def first():
			seen.append(op.Visuals.op('null_out').numpyArray()[:, :, :3].copy())

		def second():
			now = op.Visuals.op('null_out').numpyArray()[:, :, :3]
			diff = float(abs(now - seen[0]).mean())
			check(s, label, diff > 0.002, 'mean abs change %.4f' % diff)
		return [base._do(first, label + ' (a)'), base._do(second, label + ' (b)')]

	fx_rows = [['60', 'layer1', 'show', '', ''], ['62', 'layer1.effect', 'set', '2', '']]
	content = [
		base._do(resetLayers, 'reset layers'), base._setRows(fx_rows),
		base._seek(6.0), expect('effect none: solid circle', 640, 360, [1, 1, 1]),
		base._seek(11.0), expect('MIDI set effect=edges: centre empty', 640, 360, [0, 0, 0]),
		layer1(Effect='none', Visible=1), base._setRows([]), base._seek(1.0),
		layer1(Effect='invert'), expect('invert: circle black', 640, 360, [0, 0, 0]),
		expect('invert: background white', 20, 20, [1, 1, 1]),
		layer1(Effect='none'), expect('no blur: just outside the rim is black', 832, 360, [0, 0, 0]),
		layer1(Effect='blur'), base._do(lambda: check(s, 'blur: light spreads past the rim', 0.03 < pixel(832, 360)[0] < 0.5,
													 str(pixel(832, 360))), 'blur check'),
		layer1(Effect='none', Content='media', Mediafile='../media/test/test_image.png', Scale=1),
		expect('image: left of ramp dark', 8, 40, [0, 0, 0]), expect('image: right of ramp bright', 1271, 40, [1, 1, 1]),
		layer1(Mediafile='../media/test/does_not_exist.png'),
		base._do(lambda: check(s, 'missing media file does not break the engine', not op.Engine.op('engine').scriptErrors(), ''), 'missing media'),
		layer1(Content='noise', Mediafile=''),
	] + expect_changes('noise animates') + [layer1(Content='rings')] + expect_changes('rings animate') + [
		base._do(resetLayers, 'reset layers'),
	]

	return content + [
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
						  'Content', 'Effect', 'Mediafile'):
				p.val = p.default
	op.Visuals.par.Level = 1
	op.Visuals.par.Blackout = 0
	op.Visuals.par.Flash = 0
