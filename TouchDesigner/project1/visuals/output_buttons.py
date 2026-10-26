"""Output buttons: open or close the output window from the Output page."""


def onPulse(par):
	window = par.owner.op('output_window')
	if par.name == 'Openwindow':
		window.par.winopen.pulse()
	elif par.name == 'Closewindow':
		window.par.winclose.pulse()
