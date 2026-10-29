"""Tests for the Python copy of the wearable's motion processing.

Firmware/tools/motion_model.py mirrors Firmware/src/wearable/motion.cpp and
reads its numbers from Firmware/include/config.h, so these tests check the
detector design (one hit per punch, its direction, still, tilt, modes) on
made-up movements. They do not run the C++ itself.

Run from the repository root:
  python -m unittest discover -s tests -v
"""
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'Firmware', 'tools'))

import motion_model as mm  # noqa: E402

RATE = 208.0  # samples a second, as the IMU runs


class Feed:
	"""Feeds made-up samples to a model at 208 Hz and keeps every result."""

	def __init__(self, model):
		self.model = model
		self.n = 0
		self.log = []

	def run(self, seconds, accel=(0.0, 0.0, 1.0), gyro=(0.0, 0.0, 0.0), extra=None):
		"""Sensor reading for `seconds`; extra(t) adds to the acceleration,
		with t in seconds from the start of this run."""
		first = self.n
		for _ in range(int(round(seconds * RATE))):
			t = self.n / RATE
			a = list(accel)
			if extra:
				add = extra((self.n - first) / RATE)
				a = [a[i] + add[i] for i in range(3)]
			self.model.update(int(t * 1e6), int(t * 1000), a[0], a[1], a[2], *gyro)
			self.log.append((int(self.model.hit), self.model.hitDirection, int(self.model.still)))
			self.n += 1

	def hits(self):
		return mm.hitStarts([h for h, _, _ in self.log])


def pulse(start, width, size, axis):
	"""A smooth bump of `size` g on one axis, from `start` s for `width` s."""
	def extra(t):
		v = [0.0, 0.0, 0.0]
		if start <= t < start + width:
			v[axis] = size * math.sin(math.pi * (t - start) / width)
		return v
	return extra


def punch(start, axis, sign, push=3.0, stop=2.5):
	"""Speeding up one way, then a stop the other way 100 ms later."""
	a = pulse(start, 0.04, sign * push, axis)
	b = pulse(start + 0.1, 0.03, -sign * stop, axis)
	return lambda t: [x + y for x, y in zip(a(t), b(t))]


class MotionModelTests(unittest.TestCase):

	def setUp(self):
		self.config = mm.readConfig()

	def feed(self, mode='wrist', axes=(1, 2, 3)):
		f = Feed(mm.MotionModel(mode, axes, self.config))
		f.run(1.5)  # lie still: gyro calibration and tilt settle
		return f

	def test_config_is_read(self):
		self.assertIn('wrist', self.config['modes'])
		self.assertIn('ankle', self.config['modes'])
		self.assertGreater(self.config['HIT_WINDOW_MS'], self.config['HIT_HOLD_MS'])

	def test_still_and_calibration(self):
		f = Feed(mm.MotionModel('wrist', (1, 2, 3), self.config))
		bias = (0.8, -0.5, 0.3)  # a gyro that is a little off
		f.run(0.3, gyro=bias)
		self.assertFalse(f.model.still)  # not yet STILL_MS
		f.run(1.2, gyro=bias)
		self.assertTrue(f.model.gyroCalibrated)
		self.assertTrue(f.model.still)
		self.assertEqual(f.hits(), [])
		self.assertAlmostEqual(f.model.gx, 0.0, places=3)

	def test_punch_with_counter_spike_is_one_hit(self):
		f = self.feed()
		f.run(1.0, extra=punch(0.2, axis=0, sign=1))
		self.assertEqual(len(f.hits()), 1)
		self.assertEqual(f.model.hitDirection, 1)  # forward
		stillFlags = [s for _, _, s in f.log[-int(RATE):]]
		self.assertIn(0, stillFlags)  # the punch ended the stillness
		self.assertEqual(stillFlags[-1], 1)  # and holding still afterwards is a freeze

	def test_two_punches_are_two_hits(self):
		f = self.feed()
		f.run(1.2, extra=lambda t: [x + y for x, y in zip(punch(0.1, 0, 1)(t), punch(0.6, 0, 1)(t))])
		self.assertEqual(len(f.hits()), 2)

	def test_hit_is_held_for_frames(self):
		f = self.feed()
		f.run(0.6, extra=punch(0.1, 0, 1))
		start = f.hits()[0]
		held = 0
		while start + held < len(f.log) and f.log[start + held][0]:
			held += 1
		self.assertGreaterEqual(held / RATE * 1000, self.config['HIT_HOLD_MS'] - 10)
		self.assertGreater(held / RATE, 3 / 60)  # several frames at 60 fps

	def test_directions(self):
		cases = [(0, 1, 1), (0, -1, 2), (1, 1, 5), (1, -1, 6), (2, 1, 3), (2, -1, 4)]
		for axis, sign, expected in cases:
			f = self.feed()
			f.run(0.6, extra=punch(0.1, axis, sign))
			self.assertEqual((len(f.hits()), f.model.hitDirection), (1, expected), (axis, sign))

	def test_body_axes_remap(self):
		# IMU board turned a quarter: its +y points forward, its -x points left.
		f = self.feed(axes=(2, -1, 3))
		f.run(0.6, extra=punch(0.1, axis=1, sign=1))  # along sensor +y
		self.assertEqual(f.model.hitDirection, 1)  # forward
		f.run(0.6, extra=punch(0.1, axis=0, sign=1))  # along sensor +x = right
		self.assertEqual(f.model.hitDirection, 6)

	def test_gentle_movement_is_not_a_hit(self):
		f = self.feed()
		f.run(1.0, extra=pulse(0.1, 0.3, 0.8, 0))
		self.assertEqual(f.hits(), [])

	def test_ankle_needs_a_harder_hit(self):
		size = (self.config['modes']['wrist']['hitThresholdG'] + self.config['modes']['ankle']['hitThresholdG']) / 2
		for mode, expected in (('wrist', 1), ('ankle', 0)):
			f = self.feed(mode)
			f.run(0.6, extra=pulse(0.1, 0.05, size, 0))
			self.assertEqual(len(f.hits()), expected, mode)

	def test_tilt(self):
		for pitch, roll in ((45.0, 0.0), (0.0, 30.0), (-20.0, -60.0)):
			p, r = math.radians(pitch), math.radians(roll)
			gravity = (math.sin(p), math.sin(r) * math.cos(p), math.cos(r) * math.cos(p))
			f = Feed(mm.MotionModel('wrist', (1, 2, 3), self.config))
			f.run(1.0, accel=gravity)
			self.assertAlmostEqual(f.model.pitch, pitch, delta=0.5)
			self.assertAlmostEqual(f.model.roll, roll, delta=0.5)
			self.assertEqual(f.hits(), [], (pitch, roll))

	def test_activity_rises_and_falls(self):
		f = self.feed()
		self.assertLess(f.model.activity, 0.05)
		f.run(0.5, gyro=(400.0, 0.0, 0.0))
		self.assertGreater(f.model.activity, 0.5)
		f.run(2.0)
		self.assertLess(f.model.activity, 0.05)
		self.assertTrue(f.model.still)

	def test_read_recording(self):
		lines = [
			'[heartbeat] ignored',
			'#rec start, fw v0.7, wearable 1, mode ankle, body axes 1 -2 3',
			'#rec columns: ...',
			'#mark 1',
			'#rec,1000,1,0.0100,0.0200,1.0000,0.10,0.20,0.30,1.5,-2.0,0.010,0,0,1',
			'#rec,5808,5,0.01',  # cut short
			'#rec,5808,5,0.0100,0.0200,1.0000,0.10,0.20,0.30,1.5,-2.0,0.012,1,3,0',
			'#rec stop',
		]
		r = mm.readRecording(lines)
		self.assertEqual((r['mode'], r['axes'], r['skipped']), ('ankle', (1, -2, 3), 1))
		self.assertEqual(len(r['samples']), 2)
		self.assertEqual(r['marks'], [(0, '1')])
		self.assertEqual((r['samples'][1]['hit'], r['samples'][1]['dir']), (1, 3))

	def test_compare_matches_model_with_itself(self):
		# A recording whose firmware columns came from the model must match it.
		f = self.feed()
		model = f.model
		samples = []
		for i in range(int(RATE)):
			t = 2.0 + i / RATE
			a = [0.0, 0.0, 1.0]
			a[0] += punch(2.1, 0, 1)(t)[0]
			model.update(int(t * 1e6), int(t * 1000), a[0], a[1], a[2], 0.0, 0.0, 0.0)
			samples.append({'us': int(t * 1e6), 'ms': int(t * 1000), 'ax': a[0], 'ay': a[1], 'az': a[2],
				'gx': 0.0, 'gy': 0.0, 'gz': 0.0, 'hit': int(model.hit), 'dir': model.hitDirection,
				'still': int(model.still)})
		recording = {'mode': 'wrist', 'axes': (1, 2, 3), 'samples': samples}
		results = mm.run(recording, config=self.config)
		matched, firmwareOnly, modelOnly = mm.compare(recording, results)
		self.assertEqual((matched, firmwareOnly, modelOnly), (1, [], []))


if __name__ == '__main__':
	unittest.main()
