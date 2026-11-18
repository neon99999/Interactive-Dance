"""open_on_start: open the stage window when the project opens (stage Open on Start)."""


def onStart():
	# Wait a second so the rest of the network (and the output) is ready first.
	run("op.Stage.Open() if op.Stage.par.Openonstart.eval() else None", delayFrames=60)
