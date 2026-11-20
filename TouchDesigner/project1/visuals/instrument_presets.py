"""Instrument presets: choosing a Preset, or pressing Reset to Preset, sets the instrument's settings.

Every instrument keeps its presets in a table named presets: one row per
setting (par), one column per preset (named as the Preset menu entries).
Menus take the entry name, numbers the value.

While a phase change is putting a phase's settings back (Phases isApplying),
choosing a Preset does nothing: the settings come from the phase.
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
	# A phase change puts back the Preset and every setting together: then the
	# Preset must not overwrite the settings that came with it.
	phases = getattr(op, 'Phases', None)
	if par.name == 'Preset' and not (phases is not None and phases.ext.Phases.isApplying()):
		applyPreset(par.owner)


def onPulse(par):
	if par.name == 'Reset':
		applyPreset(par.owner)
