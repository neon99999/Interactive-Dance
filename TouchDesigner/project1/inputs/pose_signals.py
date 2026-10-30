"""Body tracking signals from the MediaPipe plugin's pose landmarks.

Pure Python with no TouchDesigner imports, so it is unit-tested in plain
Python (tests/test_pose_signals.py). pose_chop_callbacks feeds it the pose
results text from the plugin every frame.

Landmarks are in image coordinates: x 0-1 left to right, y 0-1 top to
bottom. Left and right are the dancer's own, as MediaPipe names them.
Sizes are measured in torso lengths (shoulders to hips), so the values stay
the same whether the dancer is near the camera or far from it. When the hips
are out of the picture (a close webcam), the torso is estimated from the
shoulder width; the shoulders must be seen.

Signals, all 0-1:
  pose_present  1 while a dancer is seen
  pose_x        where the dancer is across the picture (hips), 0 left, 1 right
  pose_hand_l   left hand height: 0 at the hips, 0.5 one torso above, 1 two torsos above
  pose_hand_r   right hand height, the same scale
  pose_spread   distance between the hands: 0 together, 1 arms stretched wide
  pose_energy   how much the arms, legs and head are moving
"""

import json
import math

NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
# Head, elbows, wrists, knees and ankles: the points whose movement counts as energy.
ENERGY_POINTS = (0, 13, 14, 15, 16, 25, 26, 27, 28)
NUM_LANDMARKS = 33

SIGNALS = ('pose_present', 'pose_x', 'pose_hand_l', 'pose_hand_r', 'pose_spread', 'pose_energy')
MIN_VISIBILITY = 0.5   # below this a landmark is treated as not seen
MIN_TORSO = 0.02       # a smaller torso (fraction of the picture) is noise, not a dancer
SPAN_TORSOS = 2.8      # wrist-to-wrist distance with arms stretched wide, in torso lengths
TORSO_PER_SHOULDER = 1.3  # torso length / shoulder width, used when the hips are not seen
ENERGY_FULL = 3.0      # average movement in torso lengths per second that reads as 1


def clamp01(value):
	return 0.0 if value < 0.0 else 1.0 if value > 1.0 else value


def parsePose(text):
	"""The first dancer's 33 landmarks as (x, y, visibility) tuples, or None if nobody is seen."""
	try:
		data = json.loads(text)
	except (ValueError, TypeError):
		return None
	if not isinstance(data, dict):
		return None
	people = (data.get('poseResults') or {}).get('landmarks') or []
	if not people or len(people[0]) < NUM_LANDMARKS:
		return None
	points = []
	for p in people[0][:NUM_LANDMARKS]:
		try:
			points.append((float(p['x']), float(p['y']), float(p.get('visibility', 1.0))))
		except (KeyError, TypeError, ValueError):
			return None
	return points


def _mid(a, b):
	return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def _dist(a, b):
	return math.hypot(a[0] - b[0], a[1] - b[1])


def measure(points):
	"""Unsmoothed signals for one frame, or None if no dancer is seen.

	A hand that is not seen is left out of the result (the tracker keeps its last value).
	"""
	if points is None:
		return None
	if min(points[L_SHOULDER][2], points[R_SHOULDER][2]) < MIN_VISIBILITY:
		return None
	shoulders = _mid(points[L_SHOULDER], points[R_SHOULDER])
	if min(points[L_HIP][2], points[R_HIP][2]) >= MIN_VISIBILITY:
		hips = _mid(points[L_HIP], points[R_HIP])
		torso = _dist(shoulders, hips)
	else:
		# Hips out of the picture (a close webcam): estimate them below the shoulders.
		torso = _dist(points[L_SHOULDER], points[R_SHOULDER]) * TORSO_PER_SHOULDER
		hips = (shoulders[0], shoulders[1] + torso)
	if torso < MIN_TORSO:
		return None
	values = {'pose_x': clamp01(hips[0])}
	wristL, wristR = points[L_WRIST], points[R_WRIST]
	if wristL[2] >= MIN_VISIBILITY:
		values['pose_hand_l'] = clamp01((hips[1] - wristL[1]) / (2.0 * torso))
	if wristR[2] >= MIN_VISIBILITY:
		values['pose_hand_r'] = clamp01((hips[1] - wristR[1]) / (2.0 * torso))
	if wristL[2] >= MIN_VISIBILITY and wristR[2] >= MIN_VISIBILITY:
		values['pose_spread'] = clamp01(_dist(wristL, wristR) / (SPAN_TORSOS * torso))
	values['_torso'] = torso
	return values


class PoseTracker:
	"""Turns landmarks, frame by frame, into smoothed signals that hold briefly through dropouts."""

	def __init__(self):
		self.reset()

	def reset(self):
		self.values = dict.fromkeys(SIGNALS, 0.0)
		self.previous = None
		self.lastTime = None
		self.lastSeen = None

	def update(self, points, now, smooth=0.1, sensitivity=1.0, hold=0.5, flipX=False):
		"""Signals for this frame. now is in seconds; smooth and hold are in seconds."""
		dt = now - self.lastTime if self.lastTime is not None else 0.0
		self.lastTime = now
		found = measure(points)
		if found is None:
			if self.lastSeen is None or now - self.lastSeen > hold:
				self.values = dict.fromkeys(SIGNALS, 0.0)
				self.previous = None
			return dict(self.values)
		self.lastSeen = now
		torso = found.pop('_torso')
		if flipX:
			found['pose_x'] = 1.0 - found['pose_x']
		energy = 0.0
		if self.previous is not None and dt > 0:
			moved = [_dist(points[i], self.previous[i]) for i in ENERGY_POINTS
				if points[i][2] >= MIN_VISIBILITY and self.previous[i][2] >= MIN_VISIBILITY]
			if moved:
				speed = sum(moved) / len(moved) / torso / dt
				energy = clamp01(speed / ENERGY_FULL * sensitivity)
		found['pose_energy'] = energy
		firstFrame = self.values['pose_present'] == 0.0
		if firstFrame or smooth <= 0:
			alpha = 1.0
		else:
			alpha = 1.0 - math.exp(-dt / smooth) if dt > 0 else 0.0
		for name, value in found.items():
			self.values[name] += alpha * (value - self.values[name])
		self.values['pose_present'] = 1.0
		self.previous = points
		return dict(self.values)


def testPose(t):
	"""A made-up dancer for the Test Pattern source: walks left and right, waves the arms.

	Returns 33 landmarks like parsePose, so the whole chain can be tried without a camera.
	"""
	cx = 0.5 + 0.25 * math.sin(t * 0.4)
	torso = 0.22
	shoulderY, hipY = 0.35, 0.35 + torso
	points = [(cx, 0.5, 1.0)] * NUM_LANDMARKS
	half = 0.06
	points[NOSE] = (cx, shoulderY - 0.1, 1.0)
	points[L_SHOULDER], points[R_SHOULDER] = (cx + half, shoulderY, 1.0), (cx - half, shoulderY, 1.0)
	points[L_HIP], points[R_HIP] = (cx + half * 0.8, hipY, 1.0), (cx - half * 0.8, hipY, 1.0)
	# Each arm swings from hanging down to straight up, out of step with the other.
	for side, (shoulder, elbow, wrist), phase in ((1, (L_SHOULDER, 13, L_WRIST), 0.0), (-1, (R_SHOULDER, 14, R_WRIST), 1.7)):
		angle = math.pi * (0.5 + 0.5 * math.sin(t * 1.1 + phase))  # 0 down, pi up
		sx, sy, _ = points[shoulder]
		reach = 0.3
		ex, ey = sx + side * math.sin(angle) * reach / 2, sy + math.cos(angle) * reach / 2
		wx, wy = sx + side * math.sin(angle) * reach, sy + math.cos(angle) * reach
		points[elbow] = (ex, ey, 1.0)
		points[wrist] = (wx, wy, 1.0)
	for knee, ankle, dx in ((25, 27, half), (26, 28, -half)):
		points[knee] = (cx + dx, hipY + 0.2, 1.0)
		points[ankle] = (cx + dx, hipY + 0.4, 1.0)
	return points
