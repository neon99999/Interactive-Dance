// LiPo battery voltage monitoring.
// Placeholder: begin() only logs. Later: read PIN_BATTERY_ADC in millivolts,
// scale by BATTERY_DIVIDER_RATIO, smooth it, and report it to the receiver.
#pragma once

namespace battery {
bool begin();
void update();
}  // namespace battery
