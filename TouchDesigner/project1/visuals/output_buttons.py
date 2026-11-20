"""Output buttons: open or close the output window, and choose its screen and borderless mode (Output page).

Monitor lists this computer's screens (monitorMenu, read live as the
parameter's menuSource). Borderless fills the chosen screen with no window
frame and hides the mouse; off, the window opens at its normal size with a
frame. output_window reads both through expressions; a change while the
window is open closes and reopens it so it takes effect at once.
"""


class _Menu:
	def __init__(self, names, labels):
		self.menuNames = names
		self.menuLabels = labels


def monitorMenu():
	"""The screens of this computer: names '0', '1' ... labels '1: 1920 x 1080 (main)'."""
	names, labels = [], []
	for m in monitors:
		names.append(str(m.index))
		labels.append('%d: %d x %d%s' % (m.index + 1, m.width, m.height, ' (main)' if m.isPrimary else ''))
	return _Menu(names or ['0'], labels or ['1'])


def _reopen(window):
	if window.isOpen:
		window.par.winclose.pulse()
		run("args[0].par.winopen.pulse()", window, delayFrames=2)


def onValueChange(par, prev):
	if par.name in ('Monitor', 'Borderless'):
		_reopen(par.owner.op('output_window'))


def onPulse(par):
	window = par.owner.op('output_window')
	if par.name == 'Openwindow':
		window.par.winopen.pulse()
	elif par.name == 'Closewindow':
		window.par.winclose.pulse()
