"""Unit tests for pose_settings' webcam matching (no TouchDesigner needed).

Run from the repository root:
  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'TouchDesigner', 'project1', 'inputs'))

import pose_settings as ps  # noqa: E402


class WebcamMatch(unittest.TestCase):

	def test_label_from_device_string(self):
		self.assertEqual(ps.deviceLabel('V1|||usb#vid_046d|||0|||0|||HD Pro Webcam C920'), 'HD Pro Webcam C920')
		self.assertEqual(ps.deviceLabel(''), '')

	def test_browser_adds_usb_id(self):
		names = ['OBS Virtual Camera', 'HD Pro Webcam C920 (046d:082d)']
		self.assertEqual(ps.matchName('HD Pro Webcam C920', names), 'HD Pro Webcam C920 (046d:082d)')

	def test_exact_and_case(self):
		self.assertEqual(ps.matchName('obs virtual camera', ['OBS Virtual Camera']), 'OBS Virtual Camera')

	def test_no_match(self):
		self.assertIsNone(ps.matchName('Logitech BRIO', ['OBS Virtual Camera']))
		self.assertIsNone(ps.matchName('', ['OBS Virtual Camera']))


class WebcamStatus(unittest.TestCase):
	C920 = 'HD Pro Webcam C920'
	LIST = ['OBS Virtual Camera', 'HD Pro Webcam C920 (046d:082d)']

	def key(self, use, label=C920, names=(), error='', seconds=60, seen=False):
		return ps.statusKey(use, label, list(names), error, seconds, seen)[0]

	def test_use_sets_both_sources(self):
		self.assertEqual(ps.USE_SOURCES['movement'], ('camera', 'off'))
		self.assertEqual(ps.USE_SOURCES['body'], ('camera', 'camera'))
		self.assertEqual(ps.USE_SOURCES['test'], ('test', 'test'))
		self.assertEqual(ps.USE_SOURCES['off'], ('off', 'off'))

	def test_off_and_test_need_no_webcam(self):
		self.assertEqual(self.key('off', label=''), 'webcam.off')
		self.assertEqual(self.key('test', label=''), 'webcam.test')

	def test_no_webcam_chosen(self):
		self.assertEqual(self.key('movement', label=''), 'webcam.nodevice')
		self.assertEqual(self.key('body', label=''), 'webcam.nodevice')

	def test_movement(self):
		self.assertEqual(self.key('movement'), 'webcam.movement')
		self.assertEqual(self.key('movement', error='Failed to open device'), 'webcam.camerror')

	def test_body_starting_then_problems(self):
		self.assertEqual(self.key('body', seconds=3), 'webcam.starting')
		self.assertEqual(self.key('body', names=['Mac Camera'], seconds=3), 'webcam.starting')
		self.assertEqual(self.key('body'), 'webcam.nolist')
		self.assertEqual(ps.statusKey('body', self.C920, ['Mac Camera'], '', 60, False),
			('webcam.nomatch', (self.C920, 'Mac Camera')))

	def test_body_dancer(self):
		self.assertEqual(self.key('body', names=self.LIST, seen=True), 'webcam.seen')
		self.assertEqual(self.key('body', names=self.LIST, seen=True, seconds=1), 'webcam.seen')
		self.assertEqual(self.key('body', names=self.LIST), 'webcam.none')

	def test_body_stalled(self):
		self.assertEqual(ps.statusKey('body', self.C920, self.LIST, '', 60, True, 5.0), ('webcam.stalled', (self.C920, 5)))
		self.assertEqual(ps.statusKey('body', self.C920, self.LIST, '', 60, True, 0.5)[0], 'webcam.seen')
		self.assertEqual(ps.statusKey('body', self.C920, self.LIST, '', 3, False, 5.0)[0], 'webcam.starting')


if __name__ == '__main__':
	unittest.main()
