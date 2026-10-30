"""Pose monitor values: one channel per value, in the order glsl_panel reads them.

Channels 0-11 are the settings and signals (VALUES below); then the 33 body
landmarks as x, y, visibility (image coordinates: x 0-1 left to right, y 0-1
top to bottom), from pose_chop_callbacks.LastPoints. Keep the order: the
shader reads them by index.
"""

VALUES = ('present', 'imagex', 'hand_l', 'hand_r', 'spread', 'energy', 'zone', 'zones', 'margin', 'flip', 'source', 'seen')
SOURCES = {'off': 0, 'camera': 1, 'test': 2}
NUM_LANDMARKS = 33


def onCook(scriptOp):
	absTime.seconds  # read every cook: the panel follows the dancer every frame
	inputs = op.Inputs
	settings = inputs.par
	pose = scriptOp.inputs[0] if scriptOp.inputs else None
	def read(name):
		chan = pose['pose_' + name] if pose is not None else None
		return float(chan.eval()) if chan is not None else 0.0
	flip = 1.0 if settings.Poseflipx.eval() else 0.0
	x = read('x')
	points = inputs.op('pose_chop_callbacks').module.LastPoints
	values = {
		'present': read('present'), 'imagex': 1.0 - x if flip else x,
		'hand_l': read('hand_l'), 'hand_r': read('hand_r'), 'spread': read('spread'), 'energy': read('energy'),
		'zone': read('zone'), 'zones': float(settings.Posezones.eval()), 'margin': float(settings.Posezonemargin.eval()),
		'flip': flip, 'source': float(SOURCES.get(settings.Posesource.eval(), 0)), 'seen': 1.0 if points else 0.0}
	scriptOp.clear()
	scriptOp.isTimeSlice = False
	scriptOp.numSamples = 1
	for name in VALUES:
		scriptOp.appendChan(name)[0] = values[name]
	for i in range(NUM_LANDMARKS):
		px, py, pv = points[i] if points and i < len(points) else (0.0, 0.0, 0.0)
		scriptOp.appendChan('p%dx' % i)[0] = px
		scriptOp.appendChan('p%dy' % i)[0] = py
		scriptOp.appendChan('p%dv' % i)[0] = pv
