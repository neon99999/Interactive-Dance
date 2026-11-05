"""Unit tests for serial_ports, the missing-port guard (no TouchDesigner needed).

Run from the repository root:
  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'TouchDesigner', 'project1', 'inputs'))

import serial_ports as spo  # noqa: E402


class IsPresent(unittest.TestCase):

	def setUp(self):
		spo._cache['time'] = -1e9

	def test_empty_port(self):
		self.assertFalse(spo.isPresent(''))
		self.assertFalse(spo.isPresent('  '))

	def test_missing_port(self):
		self.assertFalse(spo.isPresent('com987'))

	def test_listed_port_any_case(self):
		real = spo._readPorts
		spo._readPorts = lambda: ['COM3']
		try:
			self.assertTrue(spo.isPresent('com3'))
			self.assertTrue(spo.isPresent('COM3'))
			self.assertFalse(spo.isPresent('com4'))
		finally:
			spo._readPorts = real

	def test_cached_for_a_second(self):
		calls = []
		real = spo._readPorts
		spo._readPorts = lambda: calls.append(1) or ['COM3']
		try:
			for _ in range(5):
				spo.isPresent('com3')
			self.assertEqual(len(calls), 1)
		finally:
			spo._readPorts = real

	def test_device_path(self):
		self.assertTrue(spo.isPresent('/'))  # an existing path, on any system
		self.assertFalse(spo.isPresent('/dev/cu.missing-port-987'))

	def test_read_ports_returns_strings(self):
		self.assertTrue(all(isinstance(p, str) for p in spo._readPorts()))


if __name__ == '__main__':
	unittest.main()
