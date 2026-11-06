"""pose_settings: who opens the webcam, and MediaPipe's settings.

One webcam, chosen once (Camera page Device):
- Pose page Source = Webcam: MediaPipe opens it (body tracking). The camera
  motion signals, if the Camera page Source is Webcam, are measured from
  MediaPipe's picture, so both work together.
- Otherwise the Camera page opens it (camera_in), which is much lighter.
MediaPipe runs only while the Pose page Source is Webcam: stopping it when it
is not used saves frame time (it runs a web browser and the pose model).

Body Mask switches MediaPipe's image segmentation (the dancer mask that the
Video Feedback instrument's Echo: Dancer uses) on or off. MediaPipe's own
overlay drawing is always kept off, so its picture stays clean for the
visuals; pose_monitor draws the tracked body instead.
"""


def onValueChange(par, prev):
	if par.name == 'Posesource':
		mediapipe = op('mediapipe')
		if mediapipe is not None:
			mediapipe.allowCooking = par.eval() == 'camera'
		applyWebcam()
	elif par.name == 'Posemask':
		plugin = op('mediapipe/MediaPipe')
		if plugin is not None:
			plugin.par.Detectsegments = bool(par.eval())
	elif par.name == 'Cameradevice':
		applyWebcam()


def deviceLabel(device):
	"""The readable name in a Video Device In device string ('V1|||...|||HD Pro Webcam C920')."""
	return device.split('|||')[-1].strip() if device else ''


def matchName(label, names):
	"""The browser webcam name for a TouchDesigner device label, or None.

	Browsers often add a USB id ('HD Pro Webcam C920 (046d:082d)'), so the
	match ignores a trailing bracket and case."""
	if not label:
		return None
	want = label.lower()
	for name in names:
		base = name.split(' (')[0].lower()
		if name.lower() == want or base == want or want.startswith(base) or base.startswith(want):
			return name
	return None


def applyWebcam():
	"""Point camera_in and MediaPipe at the Camera page Device."""
	device = parent.Inputs.par.Cameradevice.eval()
	if not device:
		return
	camera = op('camera_in')
	if camera is not None and camera.par.device.eval() != device:
		camera.par.device = device
	plugin = op('mediapipe/MediaPipe')
	if plugin is not None:
		name = matchName(deviceLabel(device), plugin.par.Webcam.menuNames)
		if name is not None and plugin.par.Webcam.eval() != name:
			plugin.par.Webcam = name
