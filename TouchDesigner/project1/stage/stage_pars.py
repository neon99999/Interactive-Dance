"""stage_pars: the stage's own parameters go to StageExt (tests) or open/close the window."""


def onValueChange(par, prev):
	parent.Stage.ext.Stage.onParValueChange(par, prev)


def onPulse(par):
	if par.name == 'Open':
		parent.Stage.Open()
	elif par.name == 'Close':
		parent.Stage.Close()
