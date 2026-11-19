"""phases_frame: once per frame, follow the phase notes, fire triggers and write event_state."""


def onFrameStart(frame):
	parent.Phases.ext.Phases.frame()
