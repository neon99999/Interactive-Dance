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


if __name__ == '__main__':
	unittest.main()
