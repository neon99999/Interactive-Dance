// 1.8" ST7735 status screen: one row per wearable seen (live or lost, packet
// rate, lost packets, accel bars). begin() shows a colour test card first, so
// the wiring and the RX_TFT_TAB setting can be checked by eye.
#pragma once

#include <stdint.h>

namespace display {

void begin();
void update(uint32_t now);  // redraws at most every DISPLAY_REFRESH_MS

}  // namespace display
