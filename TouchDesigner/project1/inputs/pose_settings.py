"""pose_settings: MediaPipe runs only while the Pose page Source is Camera (MediaPipe).

Stopping the component when it is not used saves frame time (it runs a web
browser and the pose model).
"""


def onValueChange(par, prev):
	if par.name == 'Posesource':
		mediapipe = op('mediapipe')
		if mediapipe is not None:
			mediapipe.allowCooking = par.eval() == 'camera'
