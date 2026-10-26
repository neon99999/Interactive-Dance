"""Engine buttons: the Assignments page pulses open the tables in their own windows."""

VIEWERS = {'Editmidi': 'midi_assignments', 'Editinputs': 'input_assignments',
		   'Showerrors': 'assignment_errors', 'Showlive': 'live'}


def onPulse(par):
	name = VIEWERS.get(par.name)
	if name:
		par.owner.op(name).openViewer()
