"""Instrument presets: choosing a Preset, or pressing Reset to Preset, sets the instrument's settings.

Every instrument keeps its presets in a table named presets: one row per
setting (par), one column per preset (named as the Preset menu entries).
Menus take the entry name, numbers the value.
"""


def applyPreset(comp):
	table = comp.op('presets')
	preset = comp.par.Preset.eval()
	if table is None or table[0, preset] is None:
		return
	for r in range(1, table.numRows):
		par = comp.par[table[r, 'par'].val]
		if par is not None:
			par.val = table[r, preset].val if par.isMenu else float(table[r, preset].val)


def onValueChange(par, prev):
	if par.name == 'Preset':
		applyPreset(par.owner)


def onPulse(par):
	if par.name == 'Reset':
		applyPreset(par.owner)
