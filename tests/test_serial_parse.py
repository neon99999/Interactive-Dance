"""Unit tests for the serial line parser (no TouchDesigner needed).

Run from the repository root:
  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'TouchDesigner', 'project1', 'inputs'))

import serial_parse as sp  # noqa: E402


class ParseLine(unittest.TestCase):

	def test_plain_numbers_unnamed(self):
		self.assertEqual(sp.parseLine('0.5,1'), ({'serial_1': 0.5, 'serial_2': 1.0}, []))

	def test_plain_numbers_named(self):
		values, problems = sp.parseLine('0.5 1 7', names=['accel', 'zone'])
		self.assertEqual(values, {'serial_accel': 0.5, 'serial_zone': 1.0, 'serial_3': 7.0})
		self.assertEqual(problems, [])

	def test_separators(self):
		for line in ('1,2', '1 2', '1;2', '1\t2', '1, 2', ' 1 ,2\r\n'):
			self.assertEqual(sp.parseLine(line)[0], {'serial_1': 1.0, 'serial_2': 2.0}, line)

	def test_name_value_pairs(self):
		for line in ('accel=0.52, zone=1', 'accel:0.52 zone:1', 'accel: 0.52; zone = 1'):
			self.assertEqual(sp.parseLine(line)[0], {'serial_accel': 0.52, 'serial_zone': 1.0}, line)

	def test_bad_pieces_reported_not_raised(self):
		values, problems = sp.parseLine('0.5,abc,2')
		self.assertEqual(values, {'serial_1': 0.5, 'serial_3': 2.0})
		self.assertEqual(len(problems), 1)
		values, problems = sp.parseLine('accel=high zone=1')
		self.assertEqual(values, {'serial_zone': 1.0})
		self.assertEqual(len(problems), 1)

	def test_nan_and_empty(self):
		self.assertEqual(sp.parseLine('nan,inf')[0], {})
		self.assertEqual(sp.parseLine(''), ({}, []))
		self.assertEqual(sp.parseLine('   '), ({}, []))

	def test_log_lines_skipped(self):
		for line in ('[heartbeat] uptime 5 s, imu ok at 0x6A', '# comment 1 2', '  [imu] a=1'):
			self.assertEqual(sp.parseLine(line), ({}, []), line)
		self.assertEqual(sp.parseLine('ax=0.5 gz=-2.5')[0], {'serial_ax': 0.5, 'serial_gz': -2.5})

	def test_noise_skipped(self):
		# Wrong baud rate or a boot message joined onto the first real line.
		values, problems = sp.parseLine('\x00\x8fh"\x12J\x07w1_ax=0.5 w1_ay=1')
		self.assertEqual(values, {})
		self.assertEqual(len(problems), 1)
		# Printable junk glued to a name: that pair is dropped, the rest kept.
		self.assertEqual(sp.parseLine('h"J_____w1_ax=0.5 w1_ay=1')[0], {'serial_w1_ay': 1.0})
		self.assertEqual(sp.parseLine('a=1,b=2;c=3\td=4')[0],
			{'serial_a': 1.0, 'serial_b': 2.0, 'serial_c': 3.0, 'serial_d': 4.0})

	def test_receiver_lines(self):
		# Receiver v0.2 lines, as Firmware/src/receiver/main.cpp prints them.
		values, problems = sp.parseLine('w2_ax=0.012 w2_ay=-0.021 w2_az=1.003 w2_gx=0.4 w2_gy=-0.3 w2_gz=0.1 '
			'w2_pitch=-12.5 w2_roll=170.0 w2_act=0.031 w2_hit=1')
		self.assertEqual(problems, [])
		self.assertEqual(len(values), 10)
		self.assertEqual((values['serial_w2_pitch'], values['serial_w2_act'], values['serial_w2_hit']),
			(-12.5, 0.031, 1.0))
		self.assertEqual(sp.parseLine('w3_live=0 w3_act=0 w3_hit=0')[0],
			{'serial_w3_live': 0.0, 'serial_w3_act': 0.0, 'serial_w3_hit': 0.0})

	def test_prefix_and_names(self):
		self.assertEqual(sp.parseNames(' accel, zone ;x '), ['accel', 'zone', 'x'])
		self.assertEqual(sp.parseLine('3', prefix='s_')[0], {'s_1': 3.0})


if __name__ == '__main__':
	unittest.main()
