"""language_changed: relabel the parameters and menus when Language changes."""


def onValueChange(par, prev):
	parent.Lang.Apply()
	mappings = getattr(op, 'Mappings', None)
	if mappings is not None:
		mappings.RefreshMenus()
	phases = getattr(op, 'Phases', None)
	if phases is not None:
		phases.RefreshMenus()
	control = getattr(op, 'Control', None)
	if control is not None:
		control.Rebuild()
