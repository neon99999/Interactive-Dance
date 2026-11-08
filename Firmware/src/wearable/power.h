// Battery protection: a low-battery warning, a shutdown before the LiPo is
// run too far down, and no restart on a flat cell.
//
// The rules, on the smoothed voltage (battery.cpp; thresholds in config.h):
//   above BATTERY_LOW_MILLIVOLTS       Ok
//   at or below it                     Low: keeps running, the receiver shows it
//   at or below BATTERY_CRITICAL_MILLIVOLTS for BATTERY_CRITICAL_MS
//                                      shut down: a last BatteryStatus packet,
//                                      IMU, motor and radio off, deep sleep with
//                                      no wake-up source
//   at boot, below BATTERY_START_MILLIVOLTS
//                                      shut down at once, before the IMU and radio start
// Only RESET (or the power switch, with USB unplugged) starts it again.
//
// USB: the XIAO ESP32-C6 has no pin that sees USB power, so the firmware can
// only tell when a computer is connected (the USB Serial/JTAG sees the host's
// frames). Then nothing shuts down: the board runs from USB and the reading
// follows the charger, not the cell. A wall charger has no data, so it is not
// seen: on one the normal rules apply. The charger chip charges in deep sleep
// too, so that is safe. A board that started below BATTERY_START_MILLIVOLTS on
// a computer must reach that level before it may run on the battery alone:
// if USB is unplugged first, it shuts down after BATTERY_CRITICAL_MS.
//
// No reading (divider not wired, power switch off on USB, out-of-range
// value): nothing shuts down, and the state says NoReading.
//
// Test mode (USB keys): b<mV> Enter simulates a voltage (battery::simulate),
// x runs the start check again. While simulating, USB does not count, so a
// shutdown can be tried at the desk.
#pragma once

#include <stdint.h>

#include "protocol.h"

namespace power {

void checkAtBoot();  // after battery::begin(), before the IMU and radio; may not return
void update();       // every loop pass; may not return

dance::BatteryState state();
bool usbComputer();  // a USB computer is connected (not a wall charger)
const char* stateName(dance::BatteryState state);

}  // namespace power
