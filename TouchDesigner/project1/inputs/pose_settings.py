"""pose_settings: the Webcam page (one webcam, one Use menu, one Status line) and MediaPipe's settings.

Webcam page:
- Webcam: the one webcam the project uses.
- Use: what the webcam is for. It sets the two hidden sources:
    Off            Camerasource off,    Posesource off   (nothing opens the webcam)
    Movement only  Camerasource camera, Posesource off   (camera_in opens it; light)
    Body tracking  Camerasource camera, Posesource camera (MediaPipe opens it; the
                   camera motion signals are measured from MediaPipe's picture)
    Test           Camerasource test,   Posesource test  (no webcam needed)
- Status: read-only, says in plain words what is happening and what to do.
MediaPipe runs only while Posesource is camera: stopping it when it is not used
saves frame time (it runs a web browser and the pose model).

Body Mask (Pose page) switches MediaPipe's image segmentation (the dancer mask
that Video Feedback's Echo: Dancer uses) on or off. MediaPipe's own overlay
drawing is always kept off, so its picture stays clean for the visuals;
pose_monitor draws the tracked body instead.
"""

USE_SOURCES = {
	'off': ('off', 'off'),
	'movement': ('camera', 'off'),
	'body': ('camera', 'camera'),
	'test': ('test', 'test'),
}
STARTING_SECONDS = 15   # MediaPipe's browser takes a few seconds to list and open the webcam

# Runtime state (reset when this text changes): when Use last switched to Body tracking.
_bodySince = None


def onValueChange(par, prev):
	global _bodySince
	if par.name == 'Webcamuse':
		camera, pose = USE_SOURCES.get(par.eval(), ('off', 'off'))
		settings = parent.Inputs.par
		if par.eval() == 'body':
			_bodySince = absTime.seconds
		settings.Camerasource = camera
		settings.Posesource = pose
	elif par.name == 'Posesource':
		mediapipe = op('mediapipe')
		if mediapipe is not None:
			mediapipe.allowCooking = par.eval() == 'camera'
		applyWebcam()
	elif par.name == 'Posemask':
		plugin = op('mediapipe/MediaPipe')
		if plugin is not None:
			plugin.par.Detectsegments = bool(par.eval())
	elif par.name == 'Cameradevice':
		if parent.Inputs.par.Webcamuse.eval() == 'body':
			_bodySince = absTime.seconds
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


def webcamNames(plugin):
	"""The webcams MediaPipe's browser lists, [] while it has none (its menu source,
	the webcam_menu table inside the plugin, is empty while the browser starts)."""
	if plugin is None:
		return []
	menus = plugin.findChildren(name='webcam_menu')
	if not menus or menus[0].numRows < 1:
		return []   # reading the menu now would log a script error on the caller
	try:
		return list(plugin.par.Webcam.menuNames)
	except Exception:
		return []


def statusKey(use, label, names, cameraError, secondsOn, dancerSeen):
	"""The Status line as (language key, values to fill in). Pure, so it is unit tested.

	use: Webcamuse; label: the chosen webcam's name ('' if none); names: the
	webcams MediaPipe's browser lists; cameraError: camera_in's error text;
	secondsOn: seconds since Use switched to Body tracking; dancerSeen: pose_present."""
	if use == 'off':
		return 'webcam.off', ()
	if use == 'test':
		return 'webcam.test', ()
	if not label:
		return 'webcam.nodevice', ()
	if use == 'movement':
		if cameraError:
			return 'webcam.camerror', (label,)
		return 'webcam.movement', (label,)
	starting = secondsOn < STARTING_SECONDS
	if not names:
		return ('webcam.starting', (label,)) if starting else ('webcam.nolist', (label,))
	if matchName(label, names) is None:
		return ('webcam.starting', (label,)) if starting else ('webcam.nomatch', (label, ', '.join(names)))
	if dancerSeen:
		return 'webcam.seen', (label,)
	return ('webcam.starting', (label,)) if starting else ('webcam.none', (label,))


def statusText():
	"""The Status line in the current language (read by Webcamstatus and pose_monitor)."""
	global _bodySince
	settings = parent.Inputs.par
	use = settings.Webcamuse.eval()
	label = deviceLabel(settings.Cameradevice.eval())
	plugin = op('mediapipe/MediaPipe')
	names = webcamNames(plugin) if use == 'body' else []
	camera = op('camera_in')
	cameraError = camera.errors() if camera is not None and use == 'movement' else ''
	if _bodySince is None:
		_bodySince = absTime.seconds
	pose = op('pose_chop')
	present = pose['pose_present'] if pose is not None else None
	seen = present is not None and float(present.eval()) > 0.5
	key, values = statusKey(use, label, names, cameraError, absTime.seconds - _bodySince, seen)
	lang = getattr(op, 'Lang', None)
	text = lang.T(key) if lang is not None else key
	return text.format(*values)


def applyWebcam():
	"""Point camera_in and MediaPipe at the Webcam page's webcam."""
	device = parent.Inputs.par.Cameradevice.eval()
	if not device:
		return
	camera = op('camera_in')
	if camera is not None and camera.par.device.eval() != device:
		camera.par.device = device
	plugin = op('mediapipe/MediaPipe')
	if plugin is not None:
		name = matchName(deviceLabel(device), webcamNames(plugin))
		if name is not None and plugin.par.Webcam.eval() != name:
			plugin.par.Webcam = name
