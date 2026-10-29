"""Python copy of the wearable's motion processing (src/wearable/motion.cpp).

Used to tune the detectors on recordings made with the wearable's record
mode, and by tests/test_motion_model.py. The numbers come from
include/config.h, so a changed threshold reaches both; the logic is copied,
so a change to motion.cpp must be made here too. compare() checks a
recording's firmware results against this copy, which catches the two
drifting apart.

Record on the computer the wearable is plugged into (Firmware folder):
  pio device monitor -b 115200 -f log2file
then type r, do the moves (m before each one adds a numbered mark), type r
again and close the monitor. The log file lands in the Firmware folder.

Analyse a recording (plain Python 3.10+, no packages):
  python tools/motion_model.py recording.log [--mode wrist|ankle] [--hit 1.5]
"""

import argparse
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_H = os.path.join(HERE, '..', 'include', 'config.h')

DIRECTIONS = {0: 'none', 1: 'forward', 2: 'back', 3: 'up', 4: 'down', 5: 'left', 6: 'right'}


def readConfig(path=CONFIG_H):
	"""The numbers from config.h: {'NAME': value} plus {'modes': {'wrist': {...}}}."""
	with open(path, encoding='utf-8') as f:
		text = f.read()
	config = {}
	for name, value in re.findall(r'constexpr\s+\w+\s+(\w+)\s*=\s*([-+]?[\d.]+)f?\s*;', text):
		config[name] = float(value)
	modes = {}
	for name, values in re.findall(r'ModeSettings\s+\w+\s*=\s*\{"(\w+)",([^}]*)\}', text):
		numbers = [float(v.strip().rstrip('f')) for v in values.split(',')]
		modes[name] = dict(zip(('fullAccelG', 'fullGyroDps', 'hitThresholdG', 'stillLevel'), numbers))
	config['modes'] = modes
	return config


def _wrap180(degrees):
	while degrees > 180.0:
		degrees -= 360.0
	while degrees < -180.0:
		degrees += 360.0
	return degrees


def _bodyAxis(sensor, code):
	return sensor[code - 1] if code > 0 else -sensor[-code - 1]


def _direction(x, y, z):
	ax, ay, az = abs(x), abs(y), abs(z)
	if ax >= ay and ax >= az:
		return 1 if x > 0 else 2
	if ay >= az:
		return 5 if y > 0 else 6
	return 3 if z > 0 else 4


class MotionModel:
	"""motion.cpp, one sample at a time. Field names match motion::State."""

	def __init__(self, mode='wrist', axes=None, config=None, hitThreshold=None):
		self.c = config or readConfig()
		self.m = dict(self.c['modes'][mode])
		if hitThreshold is not None:
			self.m['hitThresholdG'] = hitThreshold
		c = self.c
		self.axes = axes or (int(c['BODY_FORWARD_AXIS']), int(c['BODY_LEFT_AXIS']), int(c['BODY_UP_AXIS']))
		self.pitch = self.roll = self.activity = 0.0
		self.hit = self.still = self.gyroCalibrated = False
		self.hitDirection = 0
		self.hits = 0
		self.size = 0.0  # acceleration with gravity removed, for tuning
		self._bias = [0.0, 0.0, 0.0]
		self._window = 0
		self._lastUs = None
		self._tiltStarted = False
		self._hitArmed = True
		self._anyHit = False
		self._hitStartMs = 0
		self._quiet = False
		self._quietSinceMs = 0

	def _calibrate(self, g, ms):
		if self._window == 0:
			self._windowStartMs = ms
			self._sum = [0.0] * 3
			self._low = list(g)
			self._high = list(g)
		for i in range(3):
			self._sum[i] += g[i]
			self._low[i] = min(self._low[i], g[i])
			self._high[i] = max(self._high[i], g[i])
		self._window += 1
		if ms - self._windowStartMs < self.c['GYRO_CALIBRATION_MS']:
			return
		mean = [v / self._window for v in self._sum]
		still = all(self._high[i] - mean[i] <= self.c['GYRO_STILL_DPS'] and
			mean[i] - self._low[i] <= self.c['GYRO_STILL_DPS'] for i in range(3))
		self._window = 0
		if still:
			self._bias = mean
			self.gyroCalibrated = True

	def update(self, us, ms, ax, ay, az, gx, gy, gz):
		"""One raw sample, sensor axes, as the firmware reads it."""
		c, m = self.c, self.m
		f, l, u = self.axes
		sa, sg = (ax, ay, az), (gx, gy, gz)
		self.ax, self.ay, self.az = _bodyAxis(sa, f), _bodyAxis(sa, l), _bodyAxis(sa, u)
		g = [_bodyAxis(sg, f), _bodyAxis(sg, l), _bodyAxis(sg, u)]
		if not self.gyroCalibrated:
			self._calibrate(g, ms)
		self.gx, self.gy, self.gz = (g[i] - self._bias[i] for i in range(3))

		dt = (us - self._lastUs) * 1e-6 if self._lastUs is not None else 0.0
		if dt > 0.1 or dt < 0:
			dt = 0.0
		self._lastUs = us

		magnitude = math.sqrt(self.ax ** 2 + self.ay ** 2 + self.az ** 2)
		self._tilt(magnitude, dt)
		self._hit(ms)
		amount = max(abs(magnitude - 1.0) / m['fullAccelG'],
			math.sqrt(self.gx ** 2 + self.gy ** 2 + self.gz ** 2) / m['fullGyroDps'])
		if dt > 0:
			target = min(1.0, amount)
			tc = c['ACTIVITY_RISE_S'] if target > self.activity else c['ACTIVITY_FALL_S']
			self.activity += (target - self.activity) * (1.0 - math.exp(-dt / tc))
		self._still(amount, ms)

	def _tilt(self, magnitude, dt):
		gravityRoll = math.degrees(math.atan2(self.ay, self.az))
		gravityPitch = math.degrees(math.atan2(self.ax, math.sqrt(self.ay ** 2 + self.az ** 2)))
		trusted = abs(magnitude - 1.0) < self.c['TILT_GRAVITY_TOLERANCE_G']
		if not self._tiltStarted:
			if trusted:
				self.pitch, self.roll, self._tiltStarted = gravityPitch, gravityRoll, True
			return
		self.roll = _wrap180(self.roll + self.gx * dt)
		self.pitch = max(-90.0, min(90.0, self.pitch - self.gy * dt))
		if trusted and dt > 0:
			k = dt / (self.c['TILT_TIME_CONSTANT_S'] + dt)
			self.roll = _wrap180(self.roll + k * _wrap180(gravityRoll - self.roll))
			self.pitch += k * (gravityPitch - self.pitch)

	def _hit(self, ms):
		p, r = math.radians(self.pitch), math.radians(self.roll)
		lx = self.ax - math.sin(p)
		ly = self.ay - math.sin(r) * math.cos(p)
		lz = self.az - math.cos(r) * math.cos(p)
		self.size = math.sqrt(lx * lx + ly * ly + lz * lz)
		threshold = self.m['hitThresholdG']
		if not self._hitArmed and ms - self._hitStartMs >= self.c['HIT_WINDOW_MS'] and self.size < threshold * 0.5:
			self._hitArmed = True
		if self._hitArmed and self.size > threshold:
			self._hitArmed = False
			self._anyHit = True
			self._hitStartMs = ms
			self.hitDirection = _direction(lx, ly, lz)
			self.hits = (self.hits + 1) % 256
		self.hit = self._anyHit and ms - self._hitStartMs < self.c['HIT_HOLD_MS']

	def _still(self, amount, ms):
		level = self.m['stillLevel']
		if amount < level:
			if not self._quiet:
				self._quiet, self._quietSinceMs = True, ms
			if ms - self._quietSinceMs >= self.c['STILL_MS']:
				self.still = True
		else:
			self._quiet = False
			if amount > 2.0 * level:
				self.still = False


# --- Recordings ---

_START = re.compile(r'#rec start, .*mode (\w+), body axes (-?\d) (-?\d) (-?\d)')


def readRecording(lines):
	"""Recording text -> {'mode', 'axes', 'samples': [...], 'marks': [(index, n)]}.

	Each sample is a dict of the #rec columns. Lines cut short (USB buffer
	full) and anything else are skipped.
	"""
	result = {'mode': None, 'axes': None, 'samples': [], 'marks': [], 'skipped': 0}
	for line in lines:
		line = line.strip()
		start = _START.search(line)
		if start:
			result['mode'] = start.group(1)
			result['axes'] = tuple(int(start.group(i)) for i in (2, 3, 4))
		elif line.startswith('#mark '):
			result['marks'].append((len(result['samples']), line[6:].strip()))
		elif line.startswith('#rec,'):
			parts = line.split(',')[1:]
			if len(parts) != 14:
				result['skipped'] += 1
				continue
			try:
				us, ms = int(parts[0]), int(parts[1])
				values = [float(v) for v in parts[2:11]]
				hit, direction, still = (int(v) for v in parts[11:14])
			except ValueError:
				result['skipped'] += 1
				continue
			names = ('ax', 'ay', 'az', 'gx', 'gy', 'gz', 'pitch', 'roll', 'act')
			sample = dict(zip(names, values), us=us, ms=ms, hit=hit, dir=direction, still=still)
			result['samples'].append(sample)
	return result


def run(recording, mode=None, hitThreshold=None, config=None):
	"""Runs the model over a recording. Returns the model's per-sample results."""
	model = MotionModel(mode or recording['mode'] or 'wrist', recording['axes'], config, hitThreshold)
	results = []
	for s in recording['samples']:
		model.update(s['us'], s['ms'], s['ax'], s['ay'], s['az'], s['gx'], s['gy'], s['gz'])
		results.append({'hit': int(model.hit), 'dir': model.hitDirection, 'still': int(model.still),
			'act': model.activity, 'pitch': model.pitch, 'roll': model.roll, 'size': model.size,
			'hits': model.hits})
	return results


def hitStarts(flags):
	"""Indexes where a 0/1 sequence goes from 0 to 1."""
	return [i for i, v in enumerate(flags) if v and (i == 0 or not flags[i - 1])]


def compare(recording, results, slack=2):
	"""Firmware hits vs model hits: (matched, firmware only, model only).

	Hits match when they start within `slack` samples and have the same
	direction. Only meaningful with the recording's own mode and thresholds.
	"""
	firmware = hitStarts([s['hit'] for s in recording['samples']])
	model = hitStarts([r['hit'] for r in results])
	matched, firmwareOnly, modelOnly = 0, [], list(model)
	for i in firmware:
		near = [j for j in modelOnly if abs(j - i) <= slack and
			results[j]['dir'] == recording['samples'][i]['dir']]
		if near:
			modelOnly.remove(near[0])
			matched += 1
		else:
			firmwareOnly.append(i)
	return matched, firmwareOnly, modelOnly


def _report(path, mode, hitThreshold):
	with open(path, encoding='utf-8', errors='replace') as f:
		recording = readRecording(f)
	samples = recording['samples']
	if not samples:
		print('No #rec lines in', path)
		return
	results = run(recording, mode, hitThreshold)
	seconds = (samples[-1]['us'] - samples[0]['us']) / 1e6
	print('%s: %d samples, %.1f s, mode %s, axes %s, %d lines skipped' % (
		os.path.basename(path), len(samples), seconds, mode or recording['mode'], recording['axes'],
		recording['skipped']))
	if mode is None and hitThreshold is None:
		matched, firmwareOnly, modelOnly = compare(recording, results)
		print('firmware vs model hits: %d match, %d firmware only, %d model only' % (
			matched, len(firmwareOnly), len(modelOnly)))
	marks = recording['marks']
	starts = hitStarts([r['hit'] for r in results])
	print('model hits: %d' % len(starts))
	for i in starts:
		peak = max(r['size'] for r in results[i:i + 40])
		mark = [n for at, n in marks if at <= i]
		print('  %7.2f s  %-7s peak %.2f g%s' % ((samples[i]['us'] - samples[0]['us']) / 1e6,
			DIRECTIONS[results[i]['dir']], peak, '  (after mark %s)' % mark[-1] if mark else ''))
	still = sum(r['still'] for r in results) / len(results)
	print('still %.0f%% of the time, activity peak %.2f' % (100 * still, max(r['act'] for r in results)))


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument('recording')
	parser.add_argument('--mode', choices=('wrist', 'ankle'), help='override the recorded mode')
	parser.add_argument('--hit', type=float, help='try another hit threshold in g')
	args = parser.parse_args()
	_report(args.recording, args.mode, args.hit)
