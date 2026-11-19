"""phases_changed: route the phases page's parameter changes to PhasesExt."""


def onValueChange(par, prev):
	if par.name == 'Phase':
		parent.Phases.LoadPhase(int(par.eval()))
	elif par.name == 'Phasenote':
		parent.Phases.ext.Phases.onPhaseNoteChange()
	elif par.name.startswith('Ev'):
		parent.Phases.ext.Phases.onEventChange(par, prev)


def onPulse(par):
	comp = parent.Phases
	if par.name == 'Clear':
		comp.ClearPhase()
	elif par.name == 'Saveshow':
		comp.SaveShow()
	elif par.name == 'Loadshow':
		comp.LoadShow()
