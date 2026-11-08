"""Python copy of the wearable's battery protection (battery.cpp + power.cpp).

Reads its numbers from include/config.h, so a changed threshold reaches both;
the logic is copied by hand, so a change to power.cpp must be made here too.
Used by tests/test_power_model.py to check the rules on made-up voltage
traces (a slow discharge, brief dips, no reading, USB) without draining a cell.
It does not run the C++ itself.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_H = os.path.join(HERE, '..', 'include', 'config.h')

NO_READING, OK, LOW, SHUTTING_DOWN = 0, 1, 2, 3   # dance::BatteryState


def readConfig(path=CONFIG_H):
	"""The numeric constants in config.h: {'NAME': value}."""
	with open(path, encoding='utf-8') as f:
		text = f.read()
	return {name: float(value) for name, value in
			re.findall(r'constexpr\s+\w+\s+(\w+)\s*=\s*([-+]?[\d.]+)f?\s*;', text)}


class Wearable:
	"""One wearable from boot: the smoothed reading and the protection rules.

	trace(t_ms) gives the ADC's battery millivolts at time t (0 or out of range
	= no reading); usb(t_ms) says whether a computer is connected."""

	def __init__(self, trace, usb=lambda t: False, simulated=False, config=None):
		self.c = config or readConfig()
		self.trace, self.usb, self.simulated = trace, usb, simulated
		self.t = 0
		self.state = NO_READING
		self.asleep = False
		self.sleptAt = None
		self.reason = ''
		self.notices = 0                  # BatteryStatus packets sent at shutdown
		self.critical = False
		self.criticalSince = 0
		self.startedLowOnUsb = False
		self.lastRead = 0
		self.lastCheck = 0
		start = int(self.c['BATTERY_START_READS'])
		self.smoothed = sum(self.trace(0) for _ in range(start)) / start
		self.lastRead = 0
		self.radio = False
		self._checkAtBoot()
		self.radio = not self.asleep

	# battery.cpp
	def millivolts(self):
		ok = self.c['BATTERY_MIN_MILLIVOLTS'] <= self.smoothed <= self.c['BATTERY_MAX_MILLIVOLTS']
		return int(self.smoothed) if ok else 0

	def _batteryUpdate(self):
		if self.t - self.lastRead < self.c['BATTERY_READ_MS']:
			return
		self.lastRead = self.t
		self.smoothed += (self.trace(self.t) - self.smoothed) * self.c['BATTERY_SMOOTHING']

	# power.cpp
	def _levelFor(self, mv, previous):
		if mv == 0:
			return NO_READING
		if mv <= self.c['BATTERY_LOW_MILLIVOLTS']:
			return LOW
		if previous == LOW and mv <= self.c['BATTERY_LOW_CLEAR_MILLIVOLTS']:
			return LOW
		return OK

	def _usbExempt(self):
		return self.usb(self.t) and not self.simulated

	def _shutDown(self, notify, reason):
		self.state = SHUTTING_DOWN
		if notify:
			self.notices = int(self.c['POWER_NOTICE_REPEATS'])
		self.radio = False
		self.asleep = True
		self.sleptAt = self.t
		self.reason = reason

	def _checkAtBoot(self):
		mv = self.millivolts()
		self.state = self._levelFor(mv, NO_READING)
		if mv == 0 or mv >= self.c['BATTERY_START_MILLIVOLTS']:
			return
		if self._usbExempt():
			self.startedLowOnUsb = True
			return
		self._shutDown(self.radio, 'start')

	def _powerUpdate(self):
		if self.t - self.lastCheck < self.c['POWER_CHECK_MS']:
			return
		self.lastCheck = self.t
		mv = self.millivolts()
		self.state = self._levelFor(mv, self.state)
		if self._usbExempt():
			if self.startedLowOnUsb and mv >= self.c['BATTERY_START_MILLIVOLTS']:
				self.startedLowOnUsb = False
			self.critical = False
			return
		tooLow = mv != 0 and (mv <= self.c['BATTERY_CRITICAL_MILLIVOLTS'] or
							  (self.startedLowOnUsb and mv < self.c['BATTERY_START_MILLIVOLTS']))
		if not tooLow:
			self.critical = False
			return
		if not self.critical:
			self.critical = True
			self.criticalSince = self.t
			return
		if self.t - self.criticalSince >= self.c['BATTERY_CRITICAL_MS']:
			self._shutDown(True, 'critical')

	def run(self, until_ms, step_ms=10):
		"""Advance the loop to until_ms (or until it sleeps). Returns self."""
		while not self.asleep and self.t < until_ms:
			self.t += step_ms
			self._batteryUpdate()
			self._powerUpdate()
		return self
