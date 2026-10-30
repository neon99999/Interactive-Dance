"""pose_chop: the pose_* body tracking signals, one sample each.

The landmarks come from the MediaPipe plugin (mediapipe/MediaPipe, its pose
output) or, for Test Dancer, from pose_signals.testPose. pose_signals does
the measuring and smoothing; the Pose page holds the settings.
"""

# Runtime state: kept between cooks, reset when this text changes or the
# project reopens (deliberately not op.storage, which TDXN would save).
_tracker = None


def onSetupParameters(scriptOp):
	return


def onPulse(par):
	return


def onCook(scriptOp):
	global _tracker
	signals = op('pose_signals').module
	settings = parent.Inputs.par
	source = settings.Posesource.eval()
	now = absTime.seconds
	if _tracker is None:
		_tracker = signals.PoseTracker()
	if source == 'camera':
		results = op('mediapipe/MediaPipe/pose')
		points = signals.parsePose(results.text) if results is not None else None
	elif source == 'test':
		points = signals.testPose(now)
	else:
		_tracker.reset()
		points = None
	values = _tracker.update(points, now, smooth=settings.Posesmooth.eval(),
		sensitivity=settings.Posesensitivity.eval(), hold=settings.Posehold.eval(),
		flipX=bool(settings.Poseflipx.eval()))
	scriptOp.clear()
	scriptOp.isTimeSlice = False
	scriptOp.numSamples = 1
	for name in signals.SIGNALS:
		scriptOp.appendChan(name)[0] = values[name]
