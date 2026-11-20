"""language_changed: relabel the parameters and menus when Language changes."""


def onValueChange(par, prev):
	parent.Lang.Apply()
	mappings = getattr(op, 'Mappings', None)
	if mappings is not None:
		mappings.RefreshMenus()
	control = getattr(op, 'Control', None)
	if control is not None:
		control.Rebuild()
