"""control_pulses: Mode / Instrument rebuild the panel; pulses are forwarded to the parameter they show."""


def onValueChange(par, prev):
	if par.name in ('Mode', 'Instrument'):
		parent.Control.ext.Control.onOwnChange(par, prev)


def onPulse(par):
	source = parent.Control.ext.Control.sourceOf(par)
	if source is not None:
		source.pulse()
