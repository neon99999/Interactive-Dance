// LiPo battery voltage monitoring.
// Reads PIN_BATTERY_ADC through the external divider, scales by
// BATTERY_DIVIDER_RATIO and smooths it. espnow_link sends the result to the
// receiver. hasReading() is false when the voltage cannot be a LiPo's, e.g.
// nothing is wired to the pin. An unwired pin floats, so it can still land in
// the valid range now and then: wire the divider before trusting the number.
// On USB the pin reads the charger, not the cell.
//
// Test mode: simulate(mV) replaces the ADC with a fixed voltage that goes
// through the same smoothing, so the protection rules (power.cpp) can be
// tried without draining a cell. simulate(0) goes back to the real pin.
#pragma once

#include <stdint.h>

namespace battery {
bool begin();
void update();

bool hasReading();
uint16_t millivolts();  // smoothed; 0 without a reading
uint8_t percent();      // rough, from the resting voltage; 0 without a reading

void simulate(uint16_t millivolts);  // 0 = real readings again
bool isSimulated();
}  // namespace battery
