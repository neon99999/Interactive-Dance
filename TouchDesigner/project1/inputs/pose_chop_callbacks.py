"""pose_chop: the pose_* body tracking signals, one sample each.

The landmarks come from the MediaPipe plugin (mediapipe/MediaPipe, its pose
output) or, for Test Dancer, from pose_signals.testPose. pose_signals does
the measuring and smoothing; the Pose page holds the settings.

The latest landmarks are kept in LastPoints for pose_points (the skeleton
drawn on pose_monitor).
"""

# Runtime state: kept between cooks, reset when this text changes or the
# project reopens (deliberately not op.storage, which TDXN would save).
_tracker = None
LastPoints = None


def onSetupParameters(scriptOp):
	return


def onPulse(par):
	return


def onCook(scriptOp):
	global _tracker, LastPoints
	signals = op('pose_signals').module
	settings = parent.Inputs.par
	source = settings.Posesource.eval()
	now = absTime.seconds
	if _tracker is None:
		_tracker = signals.PoseTracker()
	_matchMediapipeCooking(source == 'camera')
	if source == 'camera':
		results = op('mediapipe/MediaPipe/pose')
		points = signals.parsePose(results.text) if results is not None else None
	elif source == 'test':
		points = signals.testPose(now)
	else:
		_tracker.reset()
		points = None
	LastPoints = points
	values = _tracker.update(points, now, smooth=settings.Posesmooth.eval(),
		sensitivity=settings.Posesensitivity.eval(), hold=settings.Posehold.eval(),
		flipX=bool(settings.Poseflipx.eval()), zones=settings.Posezones.eval(),
		zoneMargin=settings.Posezonemargin.eval())
	scriptOp.clear()
	scriptOp.isTimeSlice = False
	scriptOp.numSamples = 1
	for name in signals.SIGNALS:
		scriptOp.appendChan(name)[0] = values[name]


def _matchMediapipeCooking(wanted):
	"""MediaPipe cooks only while Source is Camera. pose_settings switches it on a change;
	this also covers a project opened with Source already on Camera."""
	mediapipe = op('mediapipe')
	if mediapipe is not None and mediapipe.allowCooking != wanted:
		run('args[0].allowCooking = args[1]', mediapipe, wanted, delayFrames=1)
