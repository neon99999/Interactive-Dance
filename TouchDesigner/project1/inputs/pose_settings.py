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
STARTING_SECONDS = 20   # measured 11-18 s for MediaPipe to start (or restart) and send its first result

# Runtime state (reset when this text changes): when Use last switched to Body tracking.
_bodySince = None
# camera_in's Active expression reads WebcamFree: False while MediaPipe's
# browser is still letting go of the webcam, so camera_in does not try (and
# fail) to open it too early. Video Device In does not retry by itself.
try:
	WebcamFree = tdu.Dependency(True)
except NameError:   # outside TouchDesigner (unit tests)
	class _Value:
		val = True
	WebcamFree = _Value()
RELEASE_MS = 1500     # time for MediaPipe's browser to let go of the webcam
START_MS = 2500       # time for camera_in to let go before MediaPipe opens it (1 s was not always enough)
_pending = {'start': False}


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
		setMediapipeRunning(par.eval() == 'camera')
		applyWebcam()
	elif par.name == 'Posemask':
		plugin = op('mediapipe/MediaPipe')
		if plugin is not None:
			plugin.par.Detectsegments = bool(par.eval())
	elif par.name == 'Cameradevice':
		if parent.Inputs.par.Webcamuse.eval() == 'body':
			_bodySince = absTime.seconds
		applyWebcam()


def setMediapipeRunning(on):
	"""Start or stop MediaPipe, including its web browser.

	Stopping only the COMP's cooking left the browser page open, still
	holding the webcam: Movement Only then could not open it ('Failed to
	start video', and TouchDesigner stalled while camera_in retried). So the
	browser is switched off first and the COMP stops cooking a little later,
	once the page has closed and released the webcam. The other way round,
	the browser starts a moment after camera_in has let go."""
	mediapipe = op('mediapipe')
	browser = op('mediapipe/MediaPipe/webBrowser1')
	if mediapipe is None:
		return
	if on:
		mediapipe.allowCooking = True
		if browser is not None and not browser.par.Active.eval() and not _pending['start']:
			# camera_in has just been switched off: give it a moment to let go of the
			# webcam, or MediaPipe fails to start it and reloads itself (seconds lost).
			_pending['start'] = True
			run('args[0].startBrowser()', me.module, delayMilliSeconds=START_MS)
	else:
		if browser is not None and browser.par.Active.eval():
			browser.par.Active = False
			WebcamFree.val = False
		run('args[0].releasedWebcam()', me.module, delayMilliSeconds=RELEASE_MS)


def startBrowser():
	"""Switch MediaPipe's browser on, if body tracking is still wanted."""
	_pending['start'] = False
	browser = op('mediapipe/MediaPipe/webBrowser1')
	if browser is not None and parent.Inputs.par.Posesource.eval() == 'camera':
		browser.par.Active = True


def releasedWebcam(retries=3):
	"""After the browser closed: stop MediaPipe cooking and let camera_in open the
	webcam; if camera_in still cannot open it, try again a little later."""
	inputs = parent.Inputs
	mediapipe = op('mediapipe')
	if inputs.par.Posesource.eval() == 'camera':
		WebcamFree.val = True
		return
	if mediapipe is not None:
		mediapipe.allowCooking = False
	camera = op('camera_in')
	if not WebcamFree.val:
		WebcamFree.val = True
	elif retries > 0 and camera is not None and inputs.par.Camerasource.eval() == 'camera' and camera.errors():
		WebcamFree.val = False   # switches camera_in off; the next call switches it on again
	else:
		return
	if retries > 0:
		run('args[0].releasedWebcam(args[1])', me.module, retries - 1, delayMilliSeconds=RELEASE_MS)


def mediapipeRunningMatches(on):
	"""True when MediaPipe's cooking and browser already match on (cheap, for every frame)."""
	mediapipe = op('mediapipe')
	browser = op('mediapipe/MediaPipe/webBrowser1')
	if mediapipe is None:
		return True
	browserOn = bool(browser.par.Active.eval()) if browser is not None else on
	return browserOn == on and (mediapipe.allowCooking == on or not on and not browserOn)


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


STALLED_SECONDS = 3   # no new MediaPipe result for this long: say so


def statusKey(use, label, names, cameraError, secondsOn, dancerSeen, resultAge=0.0, mediapipeError=''):
	"""The Status line as (language key, values to fill in). Pure, so it is unit tested.

	use: Webcamuse; label: the chosen webcam's name ('' if none); names: the
	webcams MediaPipe's browser lists; cameraError: camera_in's error text;
	secondsOn: seconds since Use switched to Body tracking; dancerSeen: pose_present;
	resultAge: seconds since MediaPipe sent its last new result; mediapipeError:
	the plugin's error text ('Webcam failed to start...' when the webcam is busy)."""
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
	if 'webcam failed' in mediapipeError.lower():
		return 'webcam.mpbusy', (label,)
	if not names:
		return ('webcam.starting', (label,)) if starting else ('webcam.nolist', (label,))
	if matchName(label, names) is None:
		return ('webcam.starting', (label,)) if starting else ('webcam.nomatch', (label, ', '.join(names)))
	if not starting and resultAge > STALLED_SECONDS:
		return 'webcam.stalled', (label, int(resultAge))
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
	chop = op('pose_chop_callbacks')
	age = getattr(chop.module, 'ResultAge', 0.0) if chop is not None and use == 'body' else 0.0
	mpError = plugin.errors() if plugin is not None and use == 'body' else ''
	key, values = statusKey(use, label, names, cameraError, absTime.seconds - _bodySince, seen, age, mpError)
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
		# .val, not .eval(): eval raises while the stored name is not in the new menu.
		if name is not None and plugin.par.Webcam.val != name:
			plugin.par.Webcam = name
