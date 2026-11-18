"""Unit tests for the triggers (Trigger Shape) in show_logic and mapping_logic.

Run from the repository root:
  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'TouchDesigner', 'project1', 'mappings'))
sys.path.insert(0, os.path.join(HERE, '..', 'TouchDesigner', 'project1', 'engine'))

import mapping_logic as ml  # noqa: E402
import show_logic as sl  # noqa: E402

COLUMNS = list(sl.TRIGGER_COLUMNS)


def shape(**values):
	state = {'trigger.size': 0.3, 'trigger.rotate': 0.0, 'trigger.sides': 3.0,
		'trigger.x': 0.0, 'trigger.y': 0.0, 'trigger.flash': 0.0}
	state.update({'trigger.' + k: v for k, v in values.items()})
	return state


class Parse(unittest.TestCase):

	def test_only_rows_that_are_on_and_valid(self):
		rows = [COLUMNS,
			['A', '1', '1', 'midi', '60', 'pulse', '0.5'],
			['A', '2', '0', 'midi', '62', 'spin', '45'],          # off
			['A', '3', '1', 'midi', '62', 'dance', '1'],          # unknown action
			['B', '1', '1', 'serial_w1_hit', '0', 'flash', '1'],
			['E', '1', '1', 'midi', '60', 'pulse', '1'],          # no preset E
			['A', '4', '1', 'midi', 'x', 'pulse', '1']]           # bad number
		found = sl.parseTriggers(rows)
		self.assertEqual(found['A'], [('midi', 60, 'pulse', 0.5, 1)])
		self.assertEqual(found['B'], [('serial_w1_hit', 0, 'flash', 1.0, 1)])
		self.assertEqual(found['C'], [])

	def test_stored_presets_round_trip_into_the_engine(self):
		presets = {p: ml.emptyTriggers() for p in ml.PRESETS}
		presets['C'][2] = dict(on=1.0, when='serial_w2_btn', note=0.0, does='sides', amount=2.0)
		rows = ml.triggerRows(presets)
		self.assertEqual(ml.readTriggers(rows), presets)
		self.assertEqual(sl.parseTriggers(rows)['C'], [('serial_w2_btn', 0, 'sides', 2.0, 3)])

	def test_sources_and_amounts(self):
		self.assertEqual(ml.triggerSources()[:3], ['midi', 'serial_w1_hit', 'serial_w1_btn'])
		self.assertEqual(ml.triggerAmount('spin'), (45.0, -180.0, 180.0))
		self.assertEqual(set(ml.TRIGGER_ACTIONS), set(sl.TRIGGER_ACTIONS))


class Effects(unittest.TestCase):

	def test_pulse_swells_and_falls_back(self):
		events = [(1.0, 'pulse', 0.5, 0)]
		self.assertEqual(sl.triggerEffects(events, 0.9)['pulse'], 0.0)
		self.assertAlmostEqual(sl.triggerEffects(events, 1.0)['pulse'], 0.5)
		self.assertAlmostEqual(sl.triggerEffects(events, 1.0 + sl.PULSE_S)['pulse'], 0.0)

	def test_spins_add_up_eased(self):
		events = [(1.0, 'spin', 45.0, 0), (2.0, 'spin', 45.0, 0)]
		self.assertEqual(sl.triggerEffects(events, 1.0)['spin'], 0.0)
		self.assertAlmostEqual(sl.triggerEffects(events, 1.0 + sl.SPIN_S / 2)['spin'], 22.5)
		self.assertAlmostEqual(sl.triggerEffects(events, 5.0)['spin'], 90.0)

	def test_sides_wrap_round(self):
		fx = sl.triggerEffects([(t, 'sides', 1.0, 0) for t in range(10)], 20.0)
		self.assertEqual(fx['steps'], 10)
		self.assertEqual(sl.applyTriggerEffects(shape(sides=3), fx)['trigger.sides'], 3.0)
		fx['steps'] = 2
		self.assertEqual(sl.applyTriggerEffects(shape(sides=11), fx)['trigger.sides'], 3.0)

	def test_jump_is_repeatable_and_glides(self):
		events = [(1.0, 'jump', 0.5, 7.0)]
		x, y = sl.jumpTarget(7.0, 0.5)
		self.assertTrue(abs(x) <= 0.5 and abs(y) <= 0.5)
		end = sl.triggerEffects(events, 3.0)
		self.assertAlmostEqual(end['jumpx'], x)
		halfway = sl.triggerEffects(events, 1.0 + sl.JUMP_S / 2)
		self.assertAlmostEqual(halfway['jumpx'], x / 2)

	def test_flash_fades(self):
		events = [(1.0, 'flash', 1.0, 0)]
		self.assertEqual(sl.triggerEffects(events, 1.0)['flash'], 1.0)
		self.assertAlmostEqual(sl.triggerEffects(events, 1.0 + sl.FLASH_S / 2)['flash'], 0.5)

	def test_applied_to_the_shape(self):
		fx = dict(sl.emptyEffects(), pulse=1.0, spin=90.0, jumpx=0.2, flash=0.4)
		state = sl.applyTriggerEffects(shape(size=0.3, x=0.1), fx)
		self.assertAlmostEqual(state['trigger.size'], 0.6)
		self.assertEqual(state['trigger.rotate'], 90.0)
		self.assertAlmostEqual(state['trigger.x'], 0.3)
		self.assertEqual(state['trigger.flash'], 0.4)

	def test_no_instrument_no_change(self):
		state = {'layer1.scale': 1.0}
		self.assertEqual(sl.applyTriggerEffects(dict(state), dict(sl.emptyEffects(), pulse=1.0)), state)


class SongTriggers(unittest.TestCase):

	def test_each_note_uses_the_preset_of_its_moment(self):
		triggers = {'A': [('midi', 60, 'spin', 45.0, 1)], 'B': [('midi', 60, 'pulse', 1.0, 1)], 'C': [], 'D': []}
		switches = [(10.0, 'B')]
		events = sl.midiTriggerEvents([(5.0, 60), (12.0, 60), (11.0, 61)], triggers, switches, 'A')
		self.assertEqual([(t, a) for t, a, _amount, _seed in events], [(5.0, 'spin'), (12.0, 'pulse')])
		# The spin from before the switch stays.
		self.assertAlmostEqual(sl.triggerEffects(events, 30.0)['spin'], 45.0)

	def test_preset_switches_from_midi_rows(self):
		header = ['note', 'target', 'action', 'value', 'duration']
		assignments, errors = sl.parseAssignments([header, ['1', 'mapping.preset', 'set', '2', '']])
		self.assertEqual(errors, [])
		switches = sl.presetSwitches(sl.buildEvents([(4.0, 1)], assignments))
		self.assertEqual(switches, [(4.0, 'B')])
		self.assertEqual(sl.presetAt(switches, 3.0, 'A'), 'A')
		self.assertEqual(sl.presetAt(switches, 4.0, 'A'), 'B')


class Live(unittest.TestCase):

	def test_rising_edges_only(self):
		live = sl.LiveTriggers()
		rows = [('serial_w1_hit', 'spin', 30.0, 1)]
		for t, v in ((0.0, 0), (0.1, 1), (0.2, 1), (0.3, 0), (0.4, 1)):
			live.update(rows, {'serial_w1_hit': v}, t)
		self.assertAlmostEqual(live.effects(10.0)['spin'], 60.0)

	def test_old_events_fold_into_totals(self):
		live = sl.LiveTriggers()
		rows = [('serial_w1_btn', 'sides', 1.0, 1), ('serial_w1_btn', 'jump', 0.5, 2)]
		live.update(rows, {'serial_w1_btn': 1}, 0.0)
		live.update(rows, {'serial_w1_btn': 0}, 0.1)
		before = live.effects(1.0)
		live.update(rows, {'serial_w1_btn': 0}, 5.0)
		self.assertEqual(live._events, [])
		after = live.effects(5.0)
		self.assertEqual(after['steps'], 1)
		self.assertAlmostEqual(after['jumpx'], before['jumpx'])

	def test_missing_signal_is_skipped(self):
		live = sl.LiveTriggers()
		live.update([('serial_w3_hit', 'pulse', 1.0, 1)], {}, 0.0)
		self.assertEqual(live.effects(0.0)['pulse'], 0.0)


if __name__ == '__main__':
	unittest.main()
