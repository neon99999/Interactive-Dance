// Build-time settings for the receiver firmware (LOLIN NodeMCU V3, ESP8266).
// The radio channel is shared with the wearables, so it lives in protocol.h.

#pragma once

#include <stdint.h>

namespace rx {

constexpr const char* FIRMWARE_NAME = "Interactive Dance receiver";
constexpr uint8_t FIRMWARE_VERSION_MAJOR = 0;
constexpr uint8_t FIRMWARE_VERSION_MINOR = 2;

// Faster than the wearable's 115200: each wearable on fw v0.7 sends about
// 18 KB/s of text (104 lines a second), so three use about 60% of 921600 baud
// (about 92 KB/s). The USB chip on the NodeMCU handles 921600.
// TouchDesigner's inputs > Serial > Baud Rate must match.
constexpr uint32_t SERIAL_BAUD = 921600;

constexpr uint8_t MAX_WEARABLES = 8;      // wearable ids 1..8; others are ignored
constexpr uint32_t LOST_AFTER_MS = 1000;  // no packet for this long = wearable lost
// Two devices sending with the same id (flashed with the same build): shown
// as DUP on the display for this long after the last mixed-up packet.
constexpr uint32_t DUPLICATE_SHOW_MS = 3000;
constexpr uint32_t HEARTBEAT_LOG_MS = 5000;

// --- 1.8" ST7735 TFT on hardware SPI (SCL -> D5, SDA -> D7). ---
// D3, D4 and D8 are boot-mode pins on the ESP8266, so the display avoids them.
constexpr int PIN_TFT_CS = 4;    // D2
constexpr int PIN_TFT_DC = 5;    // D1
constexpr int PIN_TFT_RST = 12;  // D6 (MISO, unused: the display only receives)
constexpr uint32_t TFT_SPI_HZ = 20000000;  // conservative for jumper wires
// The display is drawn a small piece per loop pass (the title or one
// wearable's row, a few milliseconds each), so packets keep going out to
// TouchDesigner while it redraws. Every piece is redrawn this often.
constexpr uint32_t DISPLAY_REFRESH_MS = 100;
constexpr uint8_t DISPLAY_SLOTS = 3;  // rows for wearables 1..3, always shown
constexpr uint32_t DISPLAY_TEST_MS = 1500;  // colour test card shown at boot

// ST7735 module variant, named after the coloured tab on the screen's
// protective film. If red and blue are swapped, or a line of noise shows at
// an edge, try another: INITR_BLACKTAB, INITR_GREENTAB, INITR_REDTAB.
#define RX_TFT_TAB INITR_BLACKTAB

}  // namespace rx
