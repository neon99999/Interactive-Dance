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

	def test_prefix_and_names(self):
		self.assertEqual(sp.parseNames(' accel, zone ;x '), ['accel', 'zone', 'x'])
		self.assertEqual(sp.parseLine('3', prefix='s_')[0], {'s_1': 3.0})


if __name__ == '__main__':
	unittest.main()
