"""Unit tests for the phases and their placeholder events (phases/phase_logic).

Run from the repository root:
  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'TouchDesigner', 'project1', 'phases'))

import phase_logic as pl  # noqa: E402

RANGE = lambda name: (-90.0, 90.0) if name.endswith('roll') else (0.0, 1.0)  # noqa: E731


def event(**values):
	e = dict(pl.DEFAULTS, on=1.0, name='punch')
	e.update(values)
	return e


def events(*first):
	return list(first) + [dict(pl.DEFAULTS) for _ in range(pl.NUM_EVENTS - len(first))]


class Table(unittest.TestCase):

	def test_round_trip(self):
		phases = {p: pl.emptyEvents() for p in range(1, pl.NUM_PHASES + 1)}
		phases[3][1] = event(shape='circle', trigger='serial_w1_hit', link1in='serial_w1_roll', link1prop='x',
			link1from=-0.5, link1to=0.5)
		self.assertEqual(pl.readPhases(pl.phaseRows(phases)), phases)

	def test_missing_and_bad_rows(self):
		rows = [list(pl.COLUMNS), ['9', '1'] + [''] * len(pl.EVENT_FIELDS), ['2', '3', '1', 'stamp']]
		phases = pl.readPhases(rows)
		self.assertEqual(len(phases), pl.NUM_PHASES)
		self.assertEqual(phases[2][2]['name'], 'stamp')
		self.assertEqual(phases[2][2]['on'], 1.0)
		self.assertEqual(phases[2][2]['shape'], 'rectangle')


class Switches(unittest.TestCase):

	def test_phase_follows_the_last_phase_note(self):
		switches = pl.phaseSwitches([(5.0, 36), (2.0, 60), (10.0, 38), (12.0, 36)], {1: 36, 2: 38, 3: -1})
		self.assertEqual(switches, [(5.0, 1), (10.0, 2), (12.0, 1)])
		self.assertIsNone(pl.phaseAt(switches, 4.0))
		self.assertEqual(pl.phaseAt(switches, 5.0), 1)
		self.assertEqual(pl.phaseAt(switches, 11.0), 2)
		self.assertEqual(pl.phaseAt(switches, 99.0), 1)

	def test_notes_between(self):
		notes = [(1.0, 60), (1.5, 62), (2.0, 64)]
		self.assertEqual(pl.notesBetween(notes, 1.0, 2.0), [62, 64])


class Runner(unittest.TestCase):

	def run_frames(self, runner, evs, frames, phase=1):
		"""frames: [(now, signals, notes)] -> the last state list."""
		out, last = None, None
		for now, signals, notes in frames:
			dt = 0.0 if last is None else now - last
			last = now
			out = runner.update(phase, evs, signals, notes, now, dt, RANGE)
		return out

	def test_always_fades_in(self):
		r = pl.PhaseRunner()
		evs = events(event(show='always'))
		first = self.run_frames(r, evs, [(0.0, {}, [])])
		self.assertEqual(first[0]['alpha'], 0.0)
		later = self.run_frames(r, evs, [(0.1, {}, []), (0.5, {}, [])])
		self.assertEqual(later[0]['alpha'], 1.0)
		self.assertEqual(later[1]['alpha'], 0.0)  # off

	def test_timed_midi_note(self):
		r = pl.PhaseRunner()
		evs = events(event(show='timed', time=2.0, trigger='midi', note=60))
		s = self.run_frames(r, evs, [(0.0, {}, []), (1.0, {}, [62]), (2.0, {}, [])])
		self.assertEqual(s[0]['alpha'], 0.0)
		s = self.run_frames(r, evs, [(3.0, {}, [60]), (4.0, {}, [])])
		self.assertEqual(s[0]['alpha'], 1.0)
		s = self.run_frames(r, evs, [(5.1, {}, []), (5.5, {}, [])])
		self.assertEqual(s[0]['alpha'], 0.0)

	def test_timed_retrigger_restarts_the_time(self):
		r = pl.PhaseRunner()
		evs = events(event(show='timed', time=2.0, trigger='serial_w1_hit'))
		hit, rest = {'serial_w1_hit': 1.0}, {'serial_w1_hit': 0.0}
		s = self.run_frames(r, evs, [(0.0, rest, []), (1.0, hit, []), (1.5, rest, []), (2.5, hit, []),
			(3.5, rest, []), (4.0, rest, [])])
		self.assertEqual(s[0]['alpha'], 1.0)  # 1.0 + 2 s would have ended at 3.0

	def test_toggle_hit_shows_then_hides(self):
		r = pl.PhaseRunner()
		evs = events(event(show='toggle', trigger='serial_w1_hit'))
		hit, rest = {'serial_w1_hit': 1.0}, {'serial_w1_hit': 0.0}
		s = self.run_frames(r, evs, [(0.0, rest, []), (1.0, hit, []), (1.1, hit, []), (2.0, rest, [])])
		self.assertEqual(s[0]['alpha'], 1.0)  # holding the hit is one hit
		s = self.run_frames(r, evs, [(3.0, hit, []), (4.0, rest, [])])
		self.assertEqual(s[0]['alpha'], 0.0)

	def test_link_moves_a_property(self):
		r = pl.PhaseRunner()
		evs = events(event(show='always', link1in='serial_w1_roll', link1prop='rotate', link1from=-90, link1to=90,
			link2in='pose_x', link2prop='x', link2from=-1, link2to=1))
		frames = [(t / 10.0, {'serial_w1_roll': 45.0, 'pose_x': 1.0}, []) for t in range(20)]
		s = self.run_frames(r, evs, frames)
		self.assertAlmostEqual(s[0]['rotate'], 45.0, places=3)
		self.assertAlmostEqual(s[0]['x'], 1.0, places=3)
		self.assertEqual(s[0]['size'], 0.3)

	def test_missing_signal_keeps_the_base_value(self):
		r = pl.PhaseRunner()
		evs = events(event(show='always', x=0.4, link1in='serial_w3_roll', link1prop='x'))
		s = self.run_frames(r, evs, [(0.0, {}, [])])
		self.assertEqual(s[0]['x'], 0.4)

	def test_new_phase_starts_hidden(self):
		r = pl.PhaseRunner()
		evs = events(event(show='toggle', trigger='serial_w1_hit'))
		s = self.run_frames(r, evs, [(0.0, {'serial_w1_hit': 0.0}, []), (1.0, {'serial_w1_hit': 1.0}, []),
			(2.0, {'serial_w1_hit': 0.0}, [])])
		self.assertEqual(s[0]['alpha'], 1.0)
		s = self.run_frames(r, evs, [(3.0, {'serial_w1_hit': 0.0}, [])], phase=2)
		self.assertEqual(s[0]['alpha'], 0.0)

	def test_shape_and_colour_for_drawing(self):
		r = pl.PhaseRunner()
		s = self.run_frames(r, events(event(shape='triangle', colour='cyan')), [(0.0, {}, [])])
		self.assertEqual((s[0]['sides'], s[0]['colour'], s[0]['name']), (3, pl.COLOURS.index('cyan'), 'punch'))


if __name__ == '__main__':
	unittest.main()
