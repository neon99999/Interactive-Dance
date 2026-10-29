"""Wearable monitor text: the specification tables for text_left and text_right.

labels_left and labels_right both use these callbacks. Each row is one string
at x, y in pixels from the bottom left. A Text TOP's specification table only
places strings (alignment, size and colour stay per TOP), so the left column
is one Text TOP, the right-aligned values another, and glsl_panel colours them.

The card layout constants below are also read by glsl_panel (uLayout, uSlots),
so bars, lamps and text line up.
"""

WIDTH, HEIGHT = 1280, 720
PAD = 24        # margin inside each card
HEADER = 112    # header band at the top of each card
ROW = 64        # height of one signal row
LABEL_W = 104   # label column, left of the bars
VALUE_W = 104   # value column, right of the bars
TITLE_Y = HEIGHT - 60
TEXT_Y = -10    # Text TOP draws a centred line about this much above its y

SIGNAL_ROWS = (('act', 'activity'), ('gx', 'gyro x'), ('gy', 'gyro y'), ('gz', 'gyro z'),
	('pitch', 'pitch'), ('roll', 'roll'), ('hit', 'hit'), ('still', 'still'), ('btn', 'button'))
MODES = {1: 'WRIST', 2: 'ANKLE'}
DIRECTIONS = {1: 'forward', 2: 'back', 3: 'up', 4: 'down', 5: 'left', 6: 'right'}


def visibleWearables():
	"""The wearable numbers shown, left to right, from the Show Wearable parameter."""
	choice = parent.Wearables.par.Wearable.eval()
	return [1, 2, 3] if choice == 'all' else [int(choice)]


def slots():
	"""glsl_panel's uSlots: how many cards, then the 0-based wearable index in each card."""
	shown = visibleWearables()
	return [len(shown)] + [w - 1 for w in shown] + [0] * (3 - len(shown))


def rowY(row):
	return HEIGHT - HEADER - ROW * (row + 0.5)


def valueText(name, read):
	value = read(name)
	if name == 'act':
		return '%.2f' % value
	if name in ('gx', 'gy', 'gz'):
		return '%+.0f' % value
	if name in ('pitch', 'roll'):
		return '%+.0f°' % value
	if name == 'hit':
		return DIRECTIONS.get(int(read('hitdir')), '')
	return 'on' if value > 0.5 else 'off'


def onCook(scriptOp):
	values = op('panel_values')
	rightSide = scriptOp.name == 'labels_right'
	scriptOp.clear()
	scriptOp.appendRow(['x', 'y', 'text'])
	shown = visibleWearables()
	width = WIDTH / len(shown)
	for column, w in enumerate(shown):
		def read(name):
			chan = values['w%d_%s' % (w, name)] if values is not None else None
			return chan.eval() if chan is not None else 0.0
		# In a specification table every string starts at its x (the TOP's
		# alignment is not applied per row), so the values start a fixed
		# distance in from the card's right edge.
		x = (column + 1) * width - PAD - VALUE_W + 16 if rightSide else column * width + PAD + 8
		if rightSide:
			status = 'LIVE' if read('live') > 0.5 else 'NO SIGNAL'
			scriptOp.appendRow([round(x) - 16, TITLE_Y + TEXT_Y, status])
		else:
			mode = MODES.get(int(read('mode')), '')
			scriptOp.appendRow([round(x), TITLE_Y + TEXT_Y, 'W%d   %s' % (w, mode)])
		for row, (name, label) in enumerate(SIGNAL_ROWS):
			text = valueText(name, read) if rightSide else label
			scriptOp.appendRow([round(x), round(rowY(row)) + TEXT_Y, text])
