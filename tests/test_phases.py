"""Unit tests for the phases and their settings snapshots (phases/phase_logic).

Run from the repository root:
  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'TouchDesigner', 'project1', 'phases'))

import phase_logic as pl  # noqa: E402


class Keys(unittest.TestCase):

	def test_number_keys_select_phases_and_zero_is_ten(self):
		self.assertEqual([pl.keyPhase(k) for k in '1234567890'], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

	def test_other_keys_select_nothing(self):
		for key in ('a', 'p', ' ', '', '12', 'f1'):
			self.assertIsNone(pl.keyPhase(key))

	def test_ten_phases(self):
		self.assertEqual(pl.NUM_PHASES, 10)


class Snapshots(unittest.TestCase):

	def test_round_trip(self):
		snaps = {1: {'particles': {'Energy': 0.25, 'Colour': 'fire'}}, 10: {'noise': {'Visible': 1}}}
		back = pl.readSnapshots(pl.snapshotRows(snaps))
		self.assertEqual(back, {1: {'particles': {'Energy': '0.25', 'Colour': 'fire'}}, 10: {'noise': {'Visible': '1'}}})

	def test_rows_have_a_header_and_skip_bad_phases(self):
		rows = pl.snapshotRows({0: {'a': {'B': 1}}, 11: {'a': {'B': 1}}, 3: {'a': {'B': 2}}})
		self.assertEqual(rows[0], ['phase', 'comp', 'par', 'value'])
		self.assertEqual(rows[1:], [['3', 'a', 'B', '2']])

	def test_empty_or_wrong_table_is_no_snapshots(self):
		self.assertEqual(pl.readSnapshots([]), {})
		self.assertEqual(pl.readSnapshots([['phase', 'event', 'on']]), {})

	def test_values_compare_as_text(self):
		self.assertEqual(pl.valueText(0.5), '0.5')
		self.assertEqual(pl.valueText(1.0), '1')
		self.assertEqual(pl.valueText(True), '1')
		self.assertEqual(pl.valueText('fire'), 'fire')

	def test_changed_settings(self):
		stored = {'particles': {'Energy': '0.5', 'Size': '1'}}
		self.assertEqual(pl.changedSettings({'particles': {'Energy': 0.5, 'Size': 1}}, stored), {})
		self.assertEqual(pl.changedSettings({'particles': {'Energy': 0.7, 'Size': 1}}, stored),
			{'particles': {'Energy': 0.7}})
		self.assertEqual(pl.changedSettings({'noise': {'Speed': 1}}, stored), {'noise': {'Speed': 1}})


class FollowTheSong(unittest.TestCase):

	def test_switches_and_phase_at(self):
		notes = [(1.0, 60), (5.0, 62), (9.0, 60)]
		switches = pl.phaseSwitches(notes, {2: 60, 3: 62, 4: -1})
		self.assertEqual(switches, [(1.0, 2), (5.0, 3), (9.0, 2)])
		self.assertIsNone(pl.phaseAt(switches, 0.5))
		self.assertEqual(pl.phaseAt(switches, 5.0), 3)
		self.assertEqual(pl.phaseAt(switches, 20.0), 2)

	def test_phase_ten_has_a_note(self):
		self.assertEqual(pl.phaseSwitches([(2.0, 70)], {10: 70}), [(2.0, 10)])

	def test_notes_between(self):
		notes = [(1.0, 60), (2.0, 61), (3.0, 62)]
		self.assertEqual(pl.notesBetween(notes, 1.0, 3.0), [61, 62])


if __name__ == '__main__':
	unittest.main()
