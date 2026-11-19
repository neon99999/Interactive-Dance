"""phases_changed: route the phases page's parameter changes to PhasesExt."""


def onValueChange(par, prev):
	if par.name == 'Phase':
		parent.Phases.LoadPhase(int(par.eval()))
	elif par.name.startswith('Ev'):
		parent.Phases.ext.Phases.onEventChange(par, prev)


def onPulse(par):
	comp = parent.Phases
	if par.name == 'Copy':
		comp.CopyPhase(int(comp.par.Phase.eval()), int(comp.par.Copyto.eval()))
	elif par.name == 'Clear':
		comp.ClearPhase()
