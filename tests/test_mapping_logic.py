"""Unit tests for the mapping page logic (no TouchDesigner needed).

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


def slot(**values):
	s = dict(ml.SLOT_DEFAULTS)
	s.update(values)
	return s


class Catalogues(unittest.TestCase):

	def test_signals(self):
		names = ml.signalCatalogue()
		self.assertEqual(names[0], 'pose_present')
		self.assertIn('pose_zone3', names)
		self.assertIn('serial_w2_gx', names)
		self.assertIn('serial_w3_btn', names)
		self.assertEqual(len(names), len(set(names)))

	def test_targets_follow_the_engine(self):
		targets = ml.targetCatalogue(sl.knownParams())
		self.assertIn('layer4.rotate', targets)
		self.assertIn('master.flash', targets)
		self.assertNotIn('mapping.preset', targets)
		# A new engine value appears in the menu with no change here.
		self.assertIn('layer1.glow', ml.targetCatalogue(sl.knownParams() + ['layer1.glow']))

	def test_ranges(self):
		self.assertEqual(ml.signalRange('serial_w1_gx'), (-500.0, 500.0))
		self.assertEqual(ml.signalRange('serial_w3_pitch'), (-90.0, 90.0))
		self.assertEqual(ml.signalRange('serial_w1_act'), (0.0, 1.0))
		self.assertEqual(ml.signalRange('pose_hand_l'), (0.0, 1.0))
		self.assertEqual(ml.signalRange('dancer/level'), (0.0, 1.0))
		self.assertEqual(ml.targetRange('layer2.rotate'), (0.0, 360.0))
		self.assertEqual(ml.targetRange('layer1.x'), (-1.0, 1.0))
		self.assertEqual(ml.targetRange('master.flash'), (0.0, 1.0))
		self.assertEqual(ml.targetRange('layer1.glow'), (0.0, 1.0))
		self.assertEqual(ml.targetRange('particles.size', {'particles.size': (0.5, 4.0)}), (0.5, 4.0))
		self.assertEqual(ml.targetRange('layer1.x', {'particles.size': (0.5, 4.0)}), (-1.0, 1.0))

	def test_sensitivity_narrows_the_input_range(self):
		self.assertEqual(ml.inputRange('pose_hand_l', 1), (0.0, 1.0))
		self.assertEqual(ml.inputRange('pose_hand_l', 2), (0.0, 0.5))
		self.assertEqual(ml.inputRange('serial_w1_gx', 2), (-250.0, 250.0))
		self.assertEqual(ml.inputRange('pose_hand_l', 0), (0.0, 1.0))  # 0 treated as 1


class Assignments(unittest.TestCase):

	def test_rows_for_slots_that_are_on_and_complete(self):
		rows = ml.assignmentRows([
			slot(on=1, signal='pose_hand_l', target='layer1.scale', **{'from': 0.5, 'to': 2, 'smooth': 0.2}),
			slot(on=0, signal='pose_x', target='layer1.x'),
			slot(on=1, signal='', target='layer1.x'),
			slot(on=1, signal='serial_w1_gx', target='layer2.rotate', sens=2, **{'from': 0, 'to': 360}),
		], known=sl.knownParams())
		self.assertEqual(rows[0], ['signal', 'target', 'in_min', 'in_max', 'out_min', 'out_max', 'smoothing'])
		self.assertEqual(rows[1], ['pose_hand_l', 'layer1.scale', '0', '1', '0.5', '2', '0.2'])
		self.assertEqual(rows[2], ['serial_w1_gx', 'layer2.rotate', '-250', '250', '0', '360', '0.1'])
		self.assertEqual(len(rows), 3)

	def test_unknown_target_left_out(self):
		rows = ml.assignmentRows([slot(on=1, signal='pose_x', target='layer9.x')], known=sl.knownParams())
		self.assertEqual(len(rows), 1)

	def test_rows_are_valid_engine_input(self):
		rows = ml.assignmentRows([slot(on=1, signal='pose_x', target='layer1.x', **{'from': -1, 'to': 1})])
		assignments, errors = sl.parseInputAssignments(rows)
		self.assertEqual(errors, [])
		self.assertAlmostEqual(assignments[0].map(0.75), 0.5)


class Presets(unittest.TestCase):

	def test_round_trip(self):
		presets = {p: ml.emptySlots() for p in ml.PRESETS}
		presets['2'][2] = slot(on=1, signal='pose_x', target='layer1.x', **{'from': -1, 'to': 1})
		rows = ml.presetRows(presets)
		self.assertEqual(len(rows), 1 + len(ml.PRESETS) * ml.NUM_SLOTS)
		back = ml.readPresets(rows)
		self.assertEqual(back['2'][2]['signal'], 'pose_x')
		self.assertEqual(back['2'][2]['from'], -1.0)
		self.assertEqual(back['1'][0], ml.SLOT_DEFAULTS)

	def test_bad_rows_ignored_and_missing_filled(self):
		rows = [list(ml.PRESET_COLUMNS), ['Z', '1', '1', 'pose_x', 'layer1.x', '0', '1', '0', '1'],
			['a', '9', '1', 'pose_x', 'layer1.x', '0', '1', '0', '1'], ['a', '2', '1', 'pose_x', 'layer1.x', 'oops', '', '', '']]
		presets = ml.readPresets(rows)
		self.assertEqual(set(presets), set(ml.PRESETS))
		self.assertEqual(presets['1'][1]['signal'], 'pose_x')
		self.assertEqual(presets['1'][1]['from'], 0.0)  # 'oops' -> default
		self.assertEqual(presets['1'][1]['to'], 1.0)
		self.assertEqual(ml.readPresets([])['3'], ml.emptySlots())

	def test_midi_note_switches_preset_on_the_timeline(self):
		rows = [['note', 'target', 'action', 'value', 'duration'], ['70', 'mapping.preset', 'set', '2', '']]
		assignments, errors = sl.parseAssignments(rows)
		self.assertEqual(errors, [])
		events = sl.buildEvents([(10.0, 70)], assignments)
		base = sl.defaultBase()
		self.assertEqual(sl.evaluate(events, base, 5.0)['mapping.preset'], 0.0)
		self.assertEqual(ml.presetFromMidi(sl.evaluate(events, base, 12.0)['mapping.preset']), '2')

	def test_midi_preset_values(self):
		self.assertEqual([ml.presetFromMidi(v) for v in (0, 1, 2, 3, 4, 5, 1.9)], [None, '1', '2', '3', '4', '5', '2'])

	def test_old_letter_presets_read_as_phases_1_to_4(self):
		rows = [list(ml.PRESET_COLUMNS), ['B', '1', '1', 'pose_x', 'layer1.x', '-1', '1', '0', '1']]
		self.assertEqual(ml.readPresets(rows)['2'][0]['signal'], 'pose_x')
		trig = [list(ml.TRIGGER_COLUMNS), ['D', '2', '1', 'serial_w1_hit', '0', 'flash', '1']]
		self.assertEqual(ml.readTriggers(trig)['4'][1]['when'], 'serial_w1_hit')


class FourMenus(unittest.TestCase):

	def test_signal_split_and_join(self):
		for signal, parts in (('serial_w2_roll', ('wearable2', 'roll')), ('pose_x', ('body', 'pose_x')),
				('camera_left', ('camera', 'camera_left')), ('sim_level', ('test', 'sim_level')),
				('midi', ('song', 'midi')), ('', ('', ''))):
			self.assertEqual(ml.splitSignal(signal), parts)
			self.assertEqual(ml.joinSignal(*parts), signal)

	def test_inputs_are_filtered_by_source(self):
		self.assertIn('roll', ml.sourceInputs('wearable3'))
		self.assertNotIn('pose_x', ml.sourceInputs('wearable3'))
		self.assertEqual(ml.sourceInputs('camera'), ['camera_motion', 'camera_left', 'camera_right'])
		self.assertEqual(ml.sourceInputs('nothing'), [])

	def test_trigger_inputs_are_moments(self):
		self.assertEqual(ml.sourceInputs('wearable1', trigger=True), ['hit', 'btn', 'still'])
		self.assertIn('pose_zone2', ml.sourceInputs('body', trigger=True))
		self.assertNotIn('roll', ml.sourceInputs('wearable1', trigger=True))
		self.assertIn('pose_zone5', ml.triggerSources())
		self.assertEqual(ml.triggerSources()[0], 'midi')

	def test_instruments_and_settings(self):
		known = ['layer1.x', 'master.level', 'mapping.preset', 'noise.blend', 'noise.order', 'noise.speed',
			'particles.size', 'particles.order', 'video.mix', 'video.zoom', 'events.visible']
		self.assertEqual(ml.instrumentsOf(known), ['particles', 'noise', 'video', 'layer1', 'master'])
		self.assertEqual(ml.settingsOf('noise', known), ['speed'])
		self.assertEqual(ml.settingsOf('video', known), ['zoom'])
		self.assertEqual(ml.splitTarget('particles.size'), ('particles', 'size'))
		self.assertEqual(ml.joinTarget('particles', 'size'), 'particles.size')
		self.assertEqual(ml.joinTarget('particles', 'none'), '')


if __name__ == '__main__':
	unittest.main()
