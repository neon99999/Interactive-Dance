"""Pose monitor text: the specification table for text_labels.

Each row is one string at x, y in pixels from the bottom left. glsl_panel
colours the text. The layout constants are also read by glsl_panel (uLayout),
so the picture, zone strip, bars and text line up. Texts come from the
language module (op.Lang.T), so the panel follows the Language switch.
"""

WIDTH, HEIGHT = 1280, 720
PICTURE_W, PICTURE_H = 960, 540   # camera picture, top left; 16:9 like MediaPipe's 1280x720
STRIP_H = HEIGHT - PICTURE_H      # zone strip under the picture
PANEL_X = PICTURE_W               # value column on the right
PAD = 24
ROW = 70                          # one value row in the right column
ROWS_TOP = HEIGHT - 190           # centre of the first value row
TEXT_Y = -10                      # Text TOP draws a centred line about this much above its y
BARS = ('x', 'hand_l', 'hand_r', 'spread', 'energy')


def T(key):
	lang = getattr(op, 'Lang', None)
	return lang.T(key) if lang is not None else key


def rowY(row):
	return ROWS_TOP - ROW * row


def zoneCount():
	return max(1, min(5, int(op.Inputs.par.Posezones.eval())))


def onCook(scriptOp):
	settings = op.Inputs.par
	pose = op.Inputs.op('pose_chop')
	def read(name):
		chan = pose['pose_' + name] if pose is not None else None
		return float(chan.eval()) if chan is not None else 0.0
	source = settings.Posesource.eval()
	scriptOp.clear()
	scriptOp.appendRow(['x', 'y', 'text'])
	x0 = PANEL_X + PAD
	scriptOp.appendRow([x0, HEIGHT - 40 + TEXT_Y, T('pose.title')])
	scriptOp.appendRow([x0, HEIGHT - 75 + TEXT_Y, T('pose.source.' + source)])
	if source == 'off':
		status = T('pose.off')
	else:
		status = T('pose.seen') if read('present') > 0.5 else T('pose.none')
	scriptOp.appendRow([x0 + 30, HEIGHT - 115 + TEXT_Y, status])
	for row, name in enumerate(BARS):
		scriptOp.appendRow([x0, rowY(row) + 18 + TEXT_Y, T('pose.' + name)])
	zone = int(read('zone') + 0.5)
	scriptOp.appendRow([x0, 60 + TEXT_Y, '%s  %s' % (T('pose.zone'), zone if zone else '-')])
	# Zone numbers, centred in their blocks of the strip (mirrored with Flip Left/Right).
	zones = zoneCount()
	flip = bool(settings.Poseflipx.eval())
	for z in range(1, zones + 1):
		block = zones - z if flip else z - 1
		cx = (block + 0.5) * PICTURE_W / zones
		scriptOp.appendRow([round(cx) - 7, STRIP_H // 2 + TEXT_Y, str(z)])
	if source != 'camera':
		scriptOp.appendRow([PAD, HEIGHT - 40 + TEXT_Y, T('pose.nocamera')])
