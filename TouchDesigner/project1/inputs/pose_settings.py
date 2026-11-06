"""pose_settings: MediaPipe runs only while the Pose page Source is Camera (MediaPipe).

Body Mask switches MediaPipe's image segmentation (the dancer mask that the
Video Feedback instrument's Echo: Dancer uses) on or off.

Stopping the component when it is not used saves frame time (it runs a web
browser and the pose model).
"""


def onValueChange(par, prev):
	if par.name == 'Posesource':
		mediapipe = op('mediapipe')
		if mediapipe is not None:
			mediapipe.allowCooking = par.eval() == 'camera'
	elif par.name == 'Posemask':
		mediapipe = op('mediapipe/MediaPipe')
		if mediapipe is not None:
			mediapipe.par.Detectsegments = bool(par.eval())
