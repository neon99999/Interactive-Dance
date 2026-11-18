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

	def test_browser_address_port(self):
		old = 'http://localhost:49633?Webcam=HD+Pro+Webcam+C920&Resolutionw=1280.0'
		self.assertEqual(ps.addressWithPort(old, 57378), 'http://localhost:57378?Webcam=HD+Pro+Webcam+C920&Resolutionw=1280.0')
		self.assertEqual(ps.addressWithPort('http://localhost:57378/?a=1', 57378), 'http://localhost:57378/?a=1')

	def test_browser_address_webcam(self):
		old = 'http://localhost:49633?Webcam=OBS+Virtual+Camera&Resolutionw=1280.0'
		self.assertEqual(ps.addressWithPort(old, 5, "HD Pro Webcam C920 (046d:082d)"),
			'http://localhost:5?Webcam=HD+Pro+Webcam+C920+%28046d%3A082d%29&Resolutionw=1280.0')
		self.assertEqual(ps.addressWithPort('http://localhost:1?a=1', 2, 'Cam'), 'http://localhost:2?a=1&Webcam=Cam')
		self.assertEqual(ps.addressWithPort(old, 49633, None), old)

	def test_pick_webcam(self):
		names = ['v1', 'v2', 'v3']
		self.assertEqual(ps.pickWebcam(names, ['OBS Virtual Camera', 'Integrated Camera', 'HD Pro Webcam C920']), 'v3')
		self.assertEqual(ps.pickWebcam(names, ['NDI Webcam Video 1', 'Integrated Camera', 'Camo']), 'v2')
		self.assertIsNone(ps.pickWebcam(names, ['OBS Virtual Camera', 'NDI Webcam', 'mmhmm']))
		self.assertIsNone(ps.pickWebcam([], []))

	def test_should_kick(self):
		self.assertFalse(ps.shouldKick(10, 0, 0, -1e9, 0))      # still starting
		self.assertTrue(ps.shouldKick(25, 0, 20, -1e9, 0))      # started, no frames for 5 s
		self.assertFalse(ps.shouldKick(25, 0, 23, -1e9, 0))     # frames 2 s ago
		self.assertFalse(ps.shouldKick(25, 0, 20, 20, 1))       # kicked 5 s ago
		self.assertFalse(ps.shouldKick(60, 0, 20, 40, 3))       # gave up after 3 tries
		self.assertFalse(ps.shouldKick(60, None, 0, -1e9, 0))   # not running

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
		busy = 'Webcam failed to start. Is it being used somewhere else? Component reloading'
		self.assertEqual(ps.statusKey('body', self.C920, self.LIST, '', 3, False, 0.0, busy)[0], 'webcam.mpbusy')


if __name__ == '__main__':
	unittest.main()
