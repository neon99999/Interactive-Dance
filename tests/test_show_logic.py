"""Unit tests for the engine's show logic (no TouchDesigner needed).

Run from the repository root:
  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get('SHOW_LOGIC_DIR',
								   os.path.join(HERE, '..', 'TouchDesigner', 'project1', 'engine')))

import show_logic as sl  # noqa: E402

HEADER = ['note', 'target', 'action', 'value', 'duration']
BASE = {p: 0.0 for p in sl.knownParams()}
BASE.update({'layer1.opacity': 1.0, 'layer1.scale': 1.0})


def table(*rows):
	return [HEADER] + [list(r) for r in rows]


def events_for(rows, note_ons):
	assignments, errors = sl.parseAssignments(table(*rows))
	return sl.buildEvents(note_ons, assignments), errors


class ParseAssignments(unittest.TestCase):

	def test_blank_rows_are_skipped(self):
		a, errors = sl.parseAssignments(table(['', '', '', '', ''], ['60', 'layer1', 'show', '', '']))
		self.assertEqual(errors, [])
		self.assertEqual(len(a), 1)
		self.assertEqual(a[0].param, 'layer1.visible')
		self.assertEqual(a[0].row, 2)

	def test_defaults(self):
		a, _ = sl.parseAssignments(table(['60', 'layer1', 'trigger', '', ''],
										 ['61', 'Layer2.Opacity', 'Set Value', '0.5', '']))
		self.assertEqual((a[0].value, a[0].duration), (1.0, sl.TRIGGER_DEFAULT_S))
		self.assertEqual((a[1].action, a[1].param, a[1].value), ('set', 'layer2.opacity', 0.5))

	def test_invalid_rows_reported_not_raised(self):
		a, errors = sl.parseAssignments(table(
			['abc', 'layer1', 'show', '', ''],
			['200', 'layer1', 'show', '', ''],
			['60.5', 'layer1', 'show', '', ''],
			['60', 'layer9', 'show', '', ''],
			['60', 'layer1', 'explode', '', ''],
			['60', 'layer1.opacity', 'fade', '', '2'],
			['60', 'layer1.opacity', 'set', 'lots', ''],
			['60', 'layer1.opacity', 'fade', '1', '-2'],
			['60', 'layer1.opacity', 'set', 'nan', ''],
			['60', 'layer1', 'show', '', ''],
		))
		self.assertEqual(len(a), 1)
		self.assertEqual(len(errors), 9)
		self.assertTrue(all(e.startswith('row ') for e in errors))

	def test_missing_columns_and_empty_table(self):
		self.assertEqual(sl.parseAssignments([]), ([], []))
		a, errors = sl.parseAssignments([['note', 'target'], ['60', 'layer1']])
		self.assertEqual(a, [])
		self.assertEqual(len(errors), 1)


class Evaluate(unittest.TestCase):

	def test_show_hide_persist(self):
		ev, _ = events_for([['60', 'layer1', 'show', '', ''], ['62', 'layer1', 'hide', '', '']],
						   [(5.0, 60), (10.0, 62)])
		self.assertEqual(sl.evaluate(ev, BASE, 4.99)['layer1.visible'], 0.0)
		self.assertEqual(sl.evaluate(ev, BASE, 5.0)['layer1.visible'], 1.0)
		self.assertEqual(sl.evaluate(ev, BASE, 9.0)['layer1.visible'], 1.0)
		self.assertEqual(sl.evaluate(ev, BASE, 12.0)['layer1.visible'], 0.0)

	def test_seek_backward_forward_and_reset_are_deterministic(self):
		ev, _ = events_for([['60', 'layer1', 'show', '', ''], ['62', 'layer1.scale', 'set', '2', '']],
						   [(5.0, 60), (10.0, 62)])
		forward = sl.evaluate(ev, BASE, 11.0)
		back = sl.evaluate(ev, BASE, 6.0)
		self.assertEqual((back['layer1.visible'], back['layer1.scale']), (1.0, 1.0))
		self.assertEqual(sl.evaluate(ev, BASE, 11.0), forward)
		self.assertEqual(sl.evaluate(ev, BASE, 0.0), BASE)

	def test_toggle_counts_correctly(self):
		ev, _ = events_for([['60', 'layer1', 'toggle', '', '']], [(1.0, 60), (2.0, 60), (3.0, 60)])
		values = [sl.evaluate(ev, BASE, t)['layer1.visible'] for t in (0.5, 1.5, 2.5, 3.5)]
		self.assertEqual(values, [0.0, 1.0, 0.0, 1.0])

	def test_toggle_from_visible_base(self):
		base = dict(BASE, **{'layer1.visible': 1.0})
		ev, _ = events_for([['60', 'layer1', 'toggle', '', '']], [(1.0, 60)])
		self.assertEqual(sl.evaluate(ev, base, 2.0)['layer1.visible'], 0.0)

	def test_trigger_is_temporary_and_expired_triggers_do_not_apply(self):
		ev, _ = events_for([['60', 'master.flash', 'trigger', '1', '0.5']], [(5.0, 60)])
		self.assertEqual(sl.evaluate(ev, BASE, 4.9)['master.flash'], 0.0)
		self.assertEqual(sl.evaluate(ev, BASE, 5.0)['master.flash'], 1.0)
		self.assertEqual(sl.evaluate(ev, BASE, 5.49)['master.flash'], 1.0)
		self.assertEqual(sl.evaluate(ev, BASE, 5.5)['master.flash'], 0.0)
		self.assertEqual(sl.evaluate(ev, BASE, 30.0)['master.flash'], 0.0)

	def test_trigger_falls_back_to_persistent_value(self):
		ev, _ = events_for([['60', 'layer1.scale', 'set', '2', ''],
							['61', 'layer1.scale', 'trigger', '3', '1']],
						   [(1.0, 60), (2.0, 61)])
		self.assertEqual(sl.evaluate(ev, BASE, 2.5)['layer1.scale'], 3.0)
		self.assertEqual(sl.evaluate(ev, BASE, 3.5)['layer1.scale'], 2.0)

	def test_fade_duration_and_interpolation(self):
		ev, _ = events_for([['60', 'layer1.opacity', 'fade', '0', '2']], [(10.0, 60)])
		self.assertAlmostEqual(sl.evaluate(ev, BASE, 10.0)['layer1.opacity'], 1.0)
		self.assertAlmostEqual(sl.evaluate(ev, BASE, 10.5)['layer1.opacity'], 0.75)
		self.assertAlmostEqual(sl.evaluate(ev, BASE, 11.0)['layer1.opacity'], 0.5)
		self.assertAlmostEqual(sl.evaluate(ev, BASE, 12.0)['layer1.opacity'], 0.0)
		self.assertAlmostEqual(sl.evaluate(ev, BASE, 20.0)['layer1.opacity'], 0.0)

	def test_fade_interrupted_starts_from_current_value(self):
		ev, _ = events_for([['60', 'layer1.opacity', 'fade', '0', '2'],
							['61', 'layer1.opacity', 'fade', '1', '1']],
						   [(10.0, 60), (11.0, 61)])
		self.assertAlmostEqual(sl.evaluate(ev, BASE, 11.5)['layer1.opacity'], 0.75)
		self.assertAlmostEqual(sl.evaluate(ev, BASE, 12.0)['layer1.opacity'], 1.0)

	def test_show_with_duration_fades_visibility(self):
		ev, _ = events_for([['60', 'layer1', 'show', '', '1']], [(5.0, 60)])
		self.assertAlmostEqual(sl.evaluate(ev, BASE, 5.5)['layer1.visible'], 0.5)

	def test_simultaneous_notes_all_apply(self):
		ev, _ = events_for([['65', 'layer1', 'show', '', ''], ['67', 'layer2', 'show', '', '']],
						   [(20.0, 65), (20.0, 67)])
		s = sl.evaluate(ev, BASE, 20.0)
		self.assertEqual((s['layer1.visible'], s['layer2.visible']), (1.0, 1.0))

	def test_conflict_later_row_wins(self):
		rows = [['65', 'layer1.scale', 'set', '2', ''], ['67', 'layer1.scale', 'set', '3', '']]
		ev, _ = events_for(rows, [(20.0, 67), (20.0, 65)])
		self.assertEqual(sl.evaluate(ev, BASE, 20.0)['layer1.scale'], 3.0)
		ev, _ = events_for(list(reversed(rows)), [(20.0, 65), (20.0, 67)])
		self.assertEqual(sl.evaluate(ev, BASE, 20.0)['layer1.scale'], 2.0)

	def test_same_note_many_rows(self):
		ev, _ = events_for([['60', 'layer1', 'show', '', ''], ['60', 'layer1.red', 'set', '1', ''],
							['60', 'master.flash', 'trigger', '', '']], [(5.0, 60)])
		s = sl.evaluate(ev, BASE, 5.1)
		self.assertEqual((s['layer1.visible'], s['layer1.red'], s['master.flash']), (1.0, 1.0, 1.0))

	def test_pause_is_stable(self):
		ev, _ = events_for([['60', 'layer1', 'toggle', '', '']], [(5.0, 60)])
		first = sl.evaluate(ev, BASE, 6.0)
		for _ in range(100):
			self.assertEqual(sl.evaluate(ev, BASE, 6.0), first)

	def test_repeated_playback_matches(self):
		ev, _ = events_for([['60', 'layer1', 'toggle', '', ''], ['62', 'layer1.x', 'fade', '0.5', '3']],
						   [(5.0, 60), (10.0, 62), (15.0, 60)])
		times = [i * 0.25 for i in range(121)]
		run1 = [sl.evaluate(ev, BASE, t) for t in times]
		run2 = [sl.evaluate(ev, BASE, t) for t in times]
		self.assertEqual(run1, run2)

	def test_long_song_is_fast_enough(self):
		import time
		rows = [[str(60 + i), 'layer%d.opacity' % (i % 4 + 1), 'fade', str(i % 2), '0.5'] for i in range(16)]
		note_ons = [(i * 0.12, 60 + i % 16) for i in range(2000)]  # 4 minutes, 2000 notes
		ev, _ = events_for(rows, note_ons)
		start = time.perf_counter()
		for _ in range(20):
			sl.evaluate(ev, BASE, 240.0)
		per_frame_ms = (time.perf_counter() - start) / 20 * 1000
		self.assertLess(per_frame_ms, 8.0, 'evaluate took %.2f ms' % per_frame_ms)

	def test_unassigned_notes_ignored(self):
		ev, _ = events_for([['60', 'layer1', 'show', '', '']], [(5.0, 61)])
		self.assertEqual(ev, [])
		self.assertEqual(sl.evaluate(ev, BASE, 10.0), BASE)


class Inputs(unittest.TestCase):
	HEADER = ['signal', 'target', 'in_min', 'in_max', 'out_min', 'out_max', 'smoothing']

	def parse(self, *rows):
		return sl.parseInputAssignments([self.HEADER] + [list(r) for r in rows])

	def test_mapping_and_clamping(self):
		a, errors = self.parse(['sim_level', 'layer1.scale', '0.2', '0.8', '0.5', '2', ''])
		self.assertEqual(errors, [])
		self.assertAlmostEqual(a[0].map(0.5), 1.25)
		self.assertAlmostEqual(a[0].map(-1), 0.5)
		self.assertAlmostEqual(a[0].map(5), 2.0)

	def test_defaults_and_invalid(self):
		a, errors = self.parse(['sim_zone', 'layer2', '', '', '', '', ''],
							   ['', 'layer1', '', '', '', '', ''],
							   ['x', 'nowhere', '', '', '', '', ''],
							   ['x', 'layer1.x', '1', '1', '', '', ''],
							   ['x', 'layer1.x', '', '', '', '', '-1'],
							   ['x', 'layer1.x', 'low', '', '', '', ''])
		self.assertEqual(len(a), 1)
		self.assertEqual(a[0].param, 'layer2.visible')
		self.assertEqual(len(errors), 5)

	def test_missing_signal_leaves_state(self):
		a, _ = self.parse(['camera_motion', 'layer1.scale', '', '', '', '', ''])
		state = sl.InputMapper().apply(a, {}, dict(BASE), 1 / 60)
		self.assertEqual(state['layer1.scale'], 1.0)

	def test_smoothing_moves_gradually(self):
		a, _ = self.parse(['s', 'layer1.x', '', '', '', '', '1'])
		m = sl.InputMapper()
		m.apply(a, {'s': 0.0}, dict(BASE), 1 / 60)
		v = m.apply(a, {'s': 1.0}, dict(BASE), 0.1)['layer1.x']
		self.assertAlmostEqual(v, 1 - 2.718281828 ** -0.1, places=6)
		for _ in range(600):
			v = m.apply(a, {'s': 1.0}, dict(BASE), 1 / 60)['layer1.x']
		self.assertAlmostEqual(v, 1.0, places=3)

	def test_later_input_row_wins(self):
		a, _ = self.parse(['a', 'layer1.x', '', '', '0', '0', ''], ['b', 'layer1.x', '', '', '1', '1', ''])
		self.assertEqual(sl.InputMapper().apply(a, {'a': 1, 'b': 1}, dict(BASE), 0)['layer1.x'], 1.0)


class Monitor(unittest.TestCase):

	def test_note_names(self):
		self.assertEqual([sl.noteName(n) for n in (60, 61, 69, 0, 127)], ['C4', 'C#4', 'A4', 'C-1', 'G9'])

	def test_recent_notes_window(self):
		notes = [(5.0, 60), (10.0, 62), (10.0, 64), (11.0, 65)]
		self.assertEqual(sl.recentNotes(notes, 4.9, 1.5), [])
		self.assertEqual(sl.recentNotes(notes, 5.0, 1.5), [(60, 0.0)])
		self.assertEqual(sl.recentNotes(notes, 6.5, 1.5), [])
		self.assertEqual([n for n, _ in sl.recentNotes(notes, 11.2, 1.5)], [62, 64, 65])
		self.assertEqual(sl.recentNotes([], 3.0, 1.5), [])


if __name__ == '__main__':
	unittest.main()
