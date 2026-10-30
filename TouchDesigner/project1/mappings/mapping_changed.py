"""mapping_changed: route the mapping page's parameter changes to MappingsExt."""


def onValueChange(par, prev):
	ext = parent.Mappings.ext.Mappings
	if par.name == 'Preset':
		parent.Mappings.LoadPreset(par.eval())
	elif par.name.startswith('Map'):
		ext.onSlotChange(par, prev)


def onPulse(par):
	comp = parent.Mappings
	if par.name == 'Copy':
		comp.CopyPreset(comp.par.Copyfrom.eval(), comp.par.Copyto.eval())
	elif par.name == 'Clear':
		comp.ClearPreset(comp.par.Preset.eval())
	elif par.name == 'Refresh':
		comp.RefreshMenus()
