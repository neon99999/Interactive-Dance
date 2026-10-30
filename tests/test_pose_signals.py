"""Unit tests for the body tracking signals (no TouchDesigner needed).

Run from the repository root:
  python -m unittest discover -s tests -v
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'TouchDesigner', 'project1', 'inputs'))

import pose_signals as ps  # noqa: E402


def standing(cx=0.5, wristL=None, wristR=None, visibility=1.0):
	"""A dancer facing the camera: torso 0.2 tall, hands hanging at the hips unless given."""
	points = [(cx, 0.5, visibility)] * ps.NUM_LANDMARKS
	points[ps.L_SHOULDER] = (cx + 0.05, 0.4, visibility)
	points[ps.R_SHOULDER] = (cx - 0.05, 0.4, visibility)
	points[ps.L_HIP] = (cx + 0.04, 0.6, visibility)
	points[ps.R_HIP] = (cx - 0.04, 0.6, visibility)
	points[ps.L_WRIST] = wristL or (cx + 0.1, 0.6, visibility)
	points[ps.R_WRIST] = wristR or (cx - 0.1, 0.6, visibility)
	return points


def asJson(points):
	return json.dumps({'poseResults': {'landmarks': [[{'x': x, 'y': y, 'z': 0, 'visibility': v} for x, y, v in points]]}})


class ParsePose(unittest.TestCase):

	def test_reads_first_dancer(self):
		points = ps.parsePose(asJson(standing(cx=0.3)))
		self.assertEqual(len(points), 33)
		self.assertAlmostEqual(points[ps.L_HIP][0], 0.34)

	def test_nobody_or_bad_text(self):
		for text in ('', 'not json', '[]', '{}', '{"poseResults": {"landmarks": []}}',
				'{"poseResults": {"landmarks": [[{"x": 0}]]}}'):
			self.assertIsNone(ps.parsePose(text), text)

	def test_missing_visibility_counts_as_seen(self):
		text = json.dumps({'poseResults': {'landmarks': [[{'x': 0.5, 'y': 0.5, 'z': 0}] * 33]}})
		self.assertEqual(ps.parsePose(text)[0][2], 1.0)


class Measure(unittest.TestCase):

	def test_position_and_hands_down(self):
		v = ps.measure(standing(cx=0.25))
		self.assertAlmostEqual(v['pose_x'], 0.25)
		self.assertAlmostEqual(v['pose_hand_l'], 0.0)
		self.assertAlmostEqual(v['pose_hand_r'], 0.0)

	def test_hand_height_in_torso_lengths(self):
		# Torso 0.2: the left wrist one torso above the hips reads 0.5, two torsos 1.
		v = ps.measure(standing(wristL=(0.6, 0.4, 1.0), wristR=(0.4, 0.2, 1.0)))
		self.assertAlmostEqual(v['pose_hand_l'], 0.5)
		self.assertAlmostEqual(v['pose_hand_r'], 1.0)

	def test_spread(self):
		together = ps.measure(standing(wristL=(0.5, 0.5, 1.0), wristR=(0.5, 0.5, 1.0)))
		wide = ps.measure(standing(wristL=(0.8, 0.4, 1.0), wristR=(0.2, 0.4, 1.0)))
		self.assertAlmostEqual(together['pose_spread'], 0.0)
		self.assertAlmostEqual(wide['pose_spread'], 1.0)  # 0.6 apart > 2.8 torsos of 0.2

	def test_same_values_near_and_far(self):
		near = ps.measure(standing(wristL=(0.6, 0.4, 1.0)))
		far = [(0.5 + (x - 0.5) / 2, 0.5 + (y - 0.5) / 2, v) for x, y, v in standing(wristL=(0.6, 0.4, 1.0))]
		self.assertAlmostEqual(ps.measure(far)['pose_hand_l'], near['pose_hand_l'])

	def test_hips_out_of_picture(self):
		# A close webcam: shoulders 0.1 apart, hips not seen -> torso 0.13, hips 0.13 below the shoulders.
		points = standing(wristL=(0.6, 0.4, 1.0))
		points[ps.L_HIP] = (0.54, 1.2, 0.0)
		points[ps.R_HIP] = (0.46, 1.2, 0.0)
		v = ps.measure(points)
		self.assertAlmostEqual(v['pose_x'], 0.5)
		self.assertAlmostEqual(v['pose_hand_l'], 0.5)  # wrist at shoulder height: one torso above the estimated hips

	def test_unseen_dancer_and_unseen_hand(self):
		self.assertIsNone(ps.measure(None))
		self.assertIsNone(ps.measure(standing(visibility=0.1)))
		self.assertIsNone(ps.measure([(0.0, 0.0, 1.0)] * 33))  # the plugin's all-zero default
		v = ps.measure(standing(wristL=(0.6, 0.4, 0.1)))
		self.assertNotIn('pose_hand_l', v)
		self.assertNotIn('pose_spread', v)
		self.assertIn('pose_hand_r', v)


class Tracker(unittest.TestCase):

	def test_first_frame_is_not_smoothed(self):
		v = ps.PoseTracker().update(standing(cx=0.3), 0.0, smooth=1.0)
		self.assertEqual(v['pose_present'], 1.0)
		self.assertAlmostEqual(v['pose_x'], 0.3)
		self.assertEqual(v['pose_energy'], 0.0)

	def test_smoothing_moves_part_way(self):
		t = ps.PoseTracker()
		t.update(standing(cx=0.3), 0.0, smooth=0.1)
		v = t.update(standing(cx=0.7), 0.1, smooth=0.1)
		self.assertGreater(v['pose_x'], 0.3)
		self.assertLess(v['pose_x'], 0.7)
		again = t.update(standing(cx=0.7), 0.1, smooth=0.1)  # same time again (dt 0): no change, no error
		self.assertAlmostEqual(again['pose_x'], v['pose_x'])
		self.assertLess(v['pose_x'], 0.7)

	def test_energy_rises_with_movement_and_sensitivity(self):
		def energyFor(step, sensitivity):
			t = ps.PoseTracker()
			t.update(standing(), 0.0, smooth=0)
			return t.update(standing(wristL=(0.6, 0.6 - step, 1.0)), 1 / 30, smooth=0, sensitivity=sensitivity)['pose_energy']
		still = energyFor(0.0, 1.0)
		small = energyFor(0.01, 1.0)
		self.assertEqual(still, 0.0)
		self.assertGreater(small, 0.0)
		self.assertGreater(energyFor(0.01, 2.0), small)
		self.assertLessEqual(energyFor(0.5, 10.0), 1.0)

	def test_holds_through_a_short_dropout_then_clears(self):
		t = ps.PoseTracker()
		t.update(standing(cx=0.3), 0.0)
		held = t.update(None, 0.3, hold=0.5)
		self.assertEqual(held['pose_present'], 1.0)
		self.assertAlmostEqual(held['pose_x'], 0.3)
		gone = t.update(None, 0.7, hold=0.5)
		self.assertEqual(gone, dict.fromkeys(ps.SIGNALS, 0.0))

	def test_unseen_hand_keeps_its_last_value(self):
		t = ps.PoseTracker()
		t.update(standing(wristL=(0.6, 0.4, 1.0)), 0.0, smooth=0)
		v = t.update(standing(wristL=(0.6, 0.6, 0.1)), 0.1, smooth=0)
		self.assertAlmostEqual(v['pose_hand_l'], 0.5)

	def test_flip_x(self):
		v = ps.PoseTracker().update(standing(cx=0.2), 0.0, flipX=True)
		self.assertAlmostEqual(v['pose_x'], 0.8)


class Zones(unittest.TestCase):

	def test_equal_zones(self):
		self.assertEqual([ps.zoneOf(x, 3) for x in (0.0, 0.2, 0.34, 0.5, 0.7, 1.0)], [1, 1, 2, 2, 3, 3])
		self.assertEqual([ps.zoneOf(x, 2) for x in (0.1, 0.6)], [1, 2])
		self.assertEqual(ps.zoneOf(0.9, 9), 5)  # at most MAX_ZONES
		self.assertEqual(ps.zoneOf(0.9, 0), 1)

	def test_margin_stops_flicker_at_a_border(self):
		self.assertEqual(ps.zoneOf(0.36, 3, current=1, margin=0.05), 1)  # just over the border: stays
		self.assertEqual(ps.zoneOf(0.39, 3, current=1, margin=0.05), 2)  # past the margin: changes
		self.assertEqual(ps.zoneOf(0.30, 3, current=2, margin=0.05), 2)
		self.assertEqual(ps.zoneOf(0.36, 3, current=1, margin=0.0), 2)

	def test_tracker_zone_signals(self):
		t = ps.PoseTracker()
		v = t.update(standing(cx=0.8), 0.0, zones=4)
		self.assertEqual(v['pose_zone'], 4.0)
		self.assertEqual([v['pose_zone%d' % i] for i in range(1, 6)], [0, 0, 0, 1, 0])
		v = t.update(None, 1.0, hold=0.5)
		self.assertEqual(v['pose_zone'], 0.0)
		self.assertEqual(v['pose_zone4'], 0.0)

	def test_zone_follows_flip(self):
		v = ps.PoseTracker().update(standing(cx=0.1), 0.0, flipX=True, zones=3)
		self.assertEqual(v['pose_zone'], 3.0)


class TestPose(unittest.TestCase):

	def test_made_up_dancer_covers_the_ranges(self):
		t = ps.PoseTracker()
		seen = {name: [] for name in ps.SIGNALS}
		for frame in range(30 * 20):
			v = t.update(ps.testPose(frame / 30), frame / 30, smooth=0)
			for name in ps.SIGNALS:
				seen[name].append(v[name])
		self.assertEqual(min(seen['pose_present']), 1.0)
		self.assertLess(min(seen['pose_x']), 0.3)
		self.assertGreater(max(seen['pose_x']), 0.7)
		self.assertGreater(max(seen['pose_spread']) - min(seen['pose_spread']), 0.3)
		for name in ('pose_hand_l', 'pose_hand_r'):
			self.assertLess(min(seen[name]), 0.2, name)
			self.assertGreater(max(seen[name]), 0.8, name)
		self.assertGreater(max(seen['pose_energy']), 0.1)


if __name__ == '__main__':
	unittest.main()
