"""Tests for the Python copy of the wearable's battery protection.

Firmware/tools/power_model.py mirrors Firmware/src/wearable/battery.cpp and
power.cpp and reads its thresholds from Firmware/include/config.h, so these
tests check the rules (warning, shutdown after a sustained low, no shutdown on
a brief dip, no reading, start check, USB) on made-up voltage traces. They do
not run the C++ itself; the desk test with the b<mV> key does (Firmware/README.md).

Run from the repository root:
  python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'Firmware', 'tools'))

import power_model as pm  # noqa: E402

C = pm.readConfig()
S = 1000  # ms


def steady(mv):
	return lambda t: mv


def steps(*points):
	"""steps((0, 3800), (60 * S, 3250)): the voltage from each time on."""
	def trace(t):
		value = points[0][1]
		for start, mv in points:
			if t >= start:
				value = mv
		return value
	return trace


class Thresholds(unittest.TestCase):

	def test_config_values(self):
		self.assertEqual(C['BATTERY_LOW_MILLIVOLTS'], 3500)
		self.assertEqual(C['BATTERY_CRITICAL_MILLIVOLTS'], 3300)
		self.assertEqual(C['BATTERY_START_MILLIVOLTS'], 3600)
		self.assertEqual(C['BATTERY_CRITICAL_MS'], 10000)
		self.assertGreater(C['BATTERY_LOW_CLEAR_MILLIVOLTS'], C['BATTERY_LOW_MILLIVOLTS'])


class Running(unittest.TestCase):

	def test_normal_above_warning(self):
		w = pm.Wearable(steady(3900)).run(600 * S)
		self.assertFalse(w.asleep)
		self.assertEqual(w.state, pm.OK)

	def test_warning_at_3500(self):
		w = pm.Wearable(steps((0, 3800), (10 * S, 3490))).run(120 * S)
		self.assertFalse(w.asleep)
		self.assertEqual(w.state, pm.LOW)

	def test_warning_clears_only_above_hysteresis(self):
		w = pm.Wearable(steps((0, 3800), (10 * S, 3490), (120 * S, 3530))).run(240 * S)
		self.assertEqual(w.state, pm.LOW)  # 3530 is inside the hysteresis band
		w = pm.Wearable(steps((0, 3800), (10 * S, 3490), (120 * S, 3600))).run(240 * S)
		self.assertEqual(w.state, pm.OK)

	def test_sustained_critical_shuts_down(self):
		w = pm.Wearable(steps((0, 3600), (10 * S, 3250))).run(300 * S)
		self.assertTrue(w.asleep)
		self.assertEqual(w.reason, 'critical')
		self.assertEqual(w.state, pm.SHUTTING_DOWN)
		self.assertEqual(w.notices, C['POWER_NOTICE_REPEATS'])
		self.assertFalse(w.radio)

	def test_shutdown_waits_the_critical_time(self):
		# Starting just above critical, the smoothed value crosses 3300 soon after the
		# drop; the shutdown must come at least BATTERY_CRITICAL_MS after the crossing.
		w = pm.Wearable(steps((0, 3610), (10 * S, 3000)))
		crossed = None
		while not w.asleep and w.t < 300 * S:
			w.run(w.t + 10)
			if crossed is None and 0 < w.millivolts() <= C['BATTERY_CRITICAL_MILLIVOLTS']:
				crossed = w.t
		self.assertTrue(w.asleep)
		self.assertGreaterEqual(w.sleptAt - crossed, C['BATTERY_CRITICAL_MS'] - C['POWER_CHECK_MS'])

	def test_brief_dip_does_not_shut_down(self):
		# 3 s at 2.9 V (a motor buzz or a loose contact) from a healthy cell.
		w = pm.Wearable(steps((0, 3700), (30 * S, 2900), (33 * S, 3700))).run(300 * S)
		self.assertFalse(w.asleep)

	def test_dip_below_critical_shorter_than_the_wait(self):
		# Near the edge: the smoothed value goes below 3300 for about 4 s, then recovers.
		w = pm.Wearable(steps((0, 3650), (10 * S, 3310), (100 * S, 3100), (103 * S, 3450))).run(300 * S)
		self.assertFalse(w.asleep)

	def test_no_reading_never_shuts_down(self):
		for mv in (0, 1000, 5000):  # unwired pin, out of range low and high
			w = pm.Wearable(steady(mv)).run(300 * S)
			self.assertFalse(w.asleep, mv)
			self.assertEqual(w.state, pm.NO_READING)

	def test_reading_lost_while_low(self):
		# Critical, then the reading goes away before the wait is over: no shutdown.
		w = pm.Wearable(steps((0, 3610), (5 * S, 3250), (30 * S, 0))).run(400 * S)
		self.assertFalse(w.asleep)
		self.assertEqual(w.state, pm.NO_READING)

	def test_usb_computer_prevents_shutdown(self):
		w = pm.Wearable(steps((0, 3610), (10 * S, 3250)), usb=lambda t: True).run(300 * S)
		self.assertFalse(w.asleep)

	def test_simulated_voltage_ignores_usb(self):
		w = pm.Wearable(steps((0, 3610), (10 * S, 3250)), usb=lambda t: True, simulated=True).run(300 * S)
		self.assertTrue(w.asleep)


class Start(unittest.TestCase):

	def test_starts_at_or_above_3600(self):
		self.assertFalse(pm.Wearable(steady(3600)).asleep)
		self.assertFalse(pm.Wearable(steady(4100)).asleep)

	def test_refuses_below_3600_on_battery(self):
		w = pm.Wearable(steady(3550))
		self.assertTrue(w.asleep)
		self.assertEqual(w.reason, 'start')
		self.assertEqual(w.notices, 0)  # the radio is not up at boot

	def test_no_reading_at_start_runs(self):
		self.assertFalse(pm.Wearable(steady(0)).asleep)

	def test_low_start_on_usb_runs_then_unplugged(self):
		# Started at 3.45 V on a computer; unplugged at 60 s before charging to 3.6 V.
		w = pm.Wearable(steady(3450), usb=lambda t: t < 60 * S)
		self.assertFalse(w.asleep)
		w.run(60 * S)
		self.assertFalse(w.asleep)
		w.run(200 * S)
		self.assertTrue(w.asleep)
		self.assertEqual(w.reason, 'critical')
		self.assertGreaterEqual(w.sleptAt, 60 * S + C['BATTERY_CRITICAL_MS'])

	def test_low_start_on_usb_charged_then_unplugged(self):
		# Charges past 3.6 V on USB, then runs on the battery normally.
		w = pm.Wearable(steps((0, 3450), (30 * S, 3900)), usb=lambda t: t < 200 * S).run(400 * S)
		self.assertFalse(w.asleep)
		self.assertFalse(w.startedLowOnUsb)

	def test_recovery_after_charging(self):
		# After a shutdown the cell was charged; a deliberate restart (a new boot) runs.
		w = pm.Wearable(steps((0, 3600), (10 * S, 3250))).run(300 * S)
		self.assertTrue(w.asleep)
		self.assertFalse(pm.Wearable(steady(3950)).run(60 * S).asleep)
		# Rested but not charged: the cell recovers a little, still below 3.6 V.
		self.assertTrue(pm.Wearable(steady(3450)).asleep)


if __name__ == '__main__':
	unittest.main()
