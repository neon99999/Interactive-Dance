// 1.8" ST7735 status screen: a row for each of wearables 1..DISPLAY_SLOTS,
// always shown (waiting, LIVE, LOST or DUP), with packet rate, lost packets,
// accel and gyro bars, an activity bar, hit and tilt. begin() shows a colour
// test card first, so the wiring and the RX_TFT_TAB setting can be checked by
// eye. update() draws one small piece per call so the serial output to
// TouchDesigner is never held up for long.
#pragma once

#include <stdint.h>

namespace display {

void begin();
void update(uint32_t now);  // draws the title or one row; all of them every DISPLAY_REFRESH_MS

}  // namespace display
