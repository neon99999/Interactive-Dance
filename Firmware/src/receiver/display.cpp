#include "display.h"

#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <Arduino.h>
#include <SPI.h>

#include "protocol.h"
#include "radio.h"
#include "receiver_config.h"
#include "wearables.h"

namespace display {

namespace {

// Landscape: 160 x 128. Text size 1 is 6 x 8 pixels, 26 characters a line.
constexpr int16_t WIDTH = 160;
constexpr int16_t HEIGHT = 128;
constexpr int16_t TITLE_HEIGHT = 11;
constexpr int16_t ROW_TOP = 14;
constexpr int16_t ROW_HEIGHT = 38;  // name line, accel bars, gyro bars, activity line
constexpr int16_t BAR_WIDTH = 50;
constexpr int16_t BAR_HEIGHT = 6;
constexpr int16_t BAR_GAP = 3;
constexpr int ACCEL_FULL_SCALE = 2000;  // 2 g in protocol units fills a bar
constexpr int GYRO_FULL_SCALE = 5000;   // 500 dps
constexpr int16_t LINE_CHARS = 26;
constexpr int16_t LEVEL_WIDTH = 44;                    // activity bar
constexpr int16_t DETAIL_X = 2 + LEVEL_WIDTH + 4;      // markers and tilt, right of it
constexpr int16_t DETAIL_CHARS = (WIDTH - DETAIL_X) / 6;

static_assert(ROW_TOP + rx::DISPLAY_SLOTS * ROW_HEIGHT <= HEIGHT, "wearable rows do not fit on the screen");

// Project Hub theme (global-knowledge/design/hub-theme.css) in RGB565.
constexpr uint16_t ACCENT = 0xFEA0;   // --accent #ffd400 yellow: LIVE, title, activity
constexpr uint16_t ACCENT_2 = 0xFCE0; // --accent-2 #ff9d00 amber: hit, cal, DUP
constexpr uint16_t BAD = 0xFAC3;      // --bad #ff5a1f orange-red: LOST
constexpr uint16_t TEXT = 0xFF96;     // --text #fff3b0 cream
constexpr uint16_t MUTED = 0xB50B;    // --muted #b3a35c: waiting, tilt
constexpr uint16_t LINE = 0x6AC0;     // --line #6b5a00: bar centre lines
constexpr uint16_t SURFACE = 0x1081;  // --surface #14120a: empty bar tracks
constexpr uint16_t INK = ST77XX_BLACK;
constexpr uint16_t AXIS_COLOURS[3] = {BAD, ACCENT, TEXT};  // x, y, z

// The wasp-alien logo (global-knowledge/design/wasp-logo.svg), 15 x 12
// pixels, one row per entry, bit 14 = the leftmost pixel.
constexpr int16_t LOGO_W = 15;
constexpr int16_t LOGO_H = 12;
constexpr uint16_t LOGO[LOGO_H] = {
    0b100000000000001, 0b010000000000010, 0b000111111111000, 0b001111111111100,
    0b001101111101100, 0b001110111011100, 0b000111111111000, 0b000101010101000,
    0b000010101010000, 0b000001111100000, 0b000000111000000, 0b000000010000000};

Adafruit_ST7735 tft(rx::PIN_TFT_CS, rx::PIN_TFT_DC, rx::PIN_TFT_RST);

// Text is drawn into these off-screen buffers and sent to the display in one
// block. Printing straight to the display sends every pixel on its own,
// which takes about 15 ms a line and would hold back the serial output.
GFXcanvas16 lineCanvas(LINE_CHARS * 6, 8);
GFXcanvas16 detailCanvas(DETAIL_CHARS * 6, 8);

uint32_t cycleStartMs = 0;
uint8_t nextPiece = 0;  // 0 = title, 1..DISPLAY_SLOTS = a wearable's row
bool cycleRunning = false;

// A yellow and black hazard band, stripes running diagonally.
void drawHazard(int16_t x, int16_t y, int16_t w, int16_t h) {
  for (int16_t row = 0; row < h; ++row) {
    for (int16_t col = 0; col < w; ++col) {
      tft.drawPixel(x + col, y + row, ((x + col + y + row) / 6) % 2 ? INK : ACCENT);
    }
  }
}

// Boot splash: the logo and the version inside a hazard frame. It doubles as
// the wiring check: the logo must be yellow (cyan means red and blue are
// swapped) and the frame must show on all four edges; otherwise change
// RX_TFT_TAB in receiver_config.h.
void drawSplash() {
  constexpr int16_t FRAME = 6;
  constexpr int16_t SCALE = 5;
  tft.fillScreen(INK);
  drawHazard(0, 0, WIDTH, FRAME);
  drawHazard(0, HEIGHT - FRAME, WIDTH, FRAME);
  drawHazard(0, FRAME, FRAME, HEIGHT - 2 * FRAME);
  drawHazard(WIDTH - FRAME, FRAME, FRAME, HEIGHT - 2 * FRAME);
  const int16_t logoX = (WIDTH - LOGO_W * SCALE) / 2;
  const int16_t logoY = 16;
  for (int16_t row = 0; row < LOGO_H; ++row) {
    for (int16_t col = 0; col < LOGO_W; ++col) {
      if (LOGO[row] & (1 << (LOGO_W - 1 - col))) {
        tft.fillRect(logoX + col * SCALE, logoY + row * SCALE, SCALE, SCALE, ACCENT);
      }
    }
  }
  char line[24];
  snprintf(line, sizeof(line), "DANCE RX v%u.%u", rx::FIRMWARE_VERSION_MAJOR, rx::FIRMWARE_VERSION_MINOR);
  tft.setTextSize(1);
  tft.setTextColor(TEXT);
  tft.setCursor((WIDTH - static_cast<int16_t>(strlen(line)) * 6) / 2, logoY + LOGO_H * SCALE + 12);
  tft.print(line);
}

void startText(GFXcanvas16& canvas, uint16_t background) {
  canvas.fillScreen(background);
  canvas.setTextWrap(false);
  canvas.setCursor(0, 0);
}

void printText(GFXcanvas16& canvas, uint16_t colour, const char* text) {
  canvas.setTextColor(colour);
  canvas.print(text);
}

void sendText(GFXcanvas16& canvas, int16_t x, int16_t y) {
  if (!canvas.getBuffer()) return;  // out of memory at boot: no text, the bars still work
  tft.drawRGBBitmap(x, y, canvas.getBuffer(), canvas.width(), canvas.height());
}

// A bar centred on zero: grows right for positive values, left for negative.
void drawBar(int16_t x, int16_t y, int value, int fullScale, uint16_t colour) {
  const int16_t centre = x + BAR_WIDTH / 2;
  int16_t length = static_cast<int16_t>(constrain(static_cast<long>(value) * (BAR_WIDTH / 2) / fullScale,
                                                  -(BAR_WIDTH / 2), BAR_WIDTH / 2));
  const int16_t from = length >= 0 ? centre : centre + length;
  const int16_t to = length >= 0 ? centre + length : centre;
  tft.fillRect(x, y, from - x, BAR_HEIGHT, SURFACE);
  tft.fillRect(from, y, to - from, BAR_HEIGHT, colour);
  tft.fillRect(to, y, x + BAR_WIDTH - to, BAR_HEIGHT, SURFACE);
  tft.drawFastVLine(centre, y, BAR_HEIGHT, LINE);
}

// A bar filling from the left, for activity 0..MOTION_ACTIVITY_FULL.
void drawLevel(int16_t x, int16_t y, int value, uint16_t colour) {
  const int16_t length = static_cast<int16_t>(constrain(static_cast<long>(value) * LEVEL_WIDTH /
                                                        dance::MOTION_ACTIVITY_FULL, 0, LEVEL_WIDTH));
  tft.fillRect(x, y, length, BAR_HEIGHT, colour);
  tft.fillRect(x + length, y, LEVEL_WIDTH - length, BAR_HEIGHT, SURFACE);
}

const char* modeName(uint8_t mode) {
  switch (static_cast<dance::Mode>(mode)) {
    case dance::Mode::Wrist: return "wrist";
    case dance::Mode::Ankle: return "ankle";
  }
  return "";  // old firmware sends no mode
}

// Three letters, to fit the row.
const char* directionName(uint8_t direction) {
  switch (static_cast<dance::HitDirection>(direction)) {
    case dance::HitDirection::Forward: return "fwd";
    case dance::HitDirection::Back: return "bck";
    case dance::HitDirection::Up: return "up ";
    case dance::HitDirection::Down: return "dwn";
    case dance::HitDirection::Left: return "lft";
    case dance::HitDirection::Right: return "rgt";
    case dance::HitDirection::None: break;
  }
  return "HIT";
}

void drawTitle(uint32_t now) {
  // Wearables beyond the rows on screen still reach TouchDesigner; count them.
  uint8_t others = 0;
  for (uint8_t i = rx::DISPLAY_SLOTS; i < rx::MAX_WEARABLES; ++i) others += rx::wearables[i].live ? 1 : 0;
  char line[48];  // anything past LINE_CHARS is cut off at the canvas edge
  char extra[8] = "";
  if (others) snprintf(extra, sizeof(extra), " +%u", others);
  snprintf(line, sizeof(line), "RX v%u.%u ch %u%-4s%7lus", rx::FIRMWARE_VERSION_MAJOR, rx::FIRMWARE_VERSION_MINOR,
           dance::ESPNOW_CHANNEL, extra, static_cast<unsigned long>(now / 1000));
  startText(lineCanvas, ACCENT);
  printText(lineCanvas, INK, line);
  sendText(lineCanvas, 2, 2);
}

void drawRow(uint8_t slot, uint32_t now) {
  const uint8_t id = slot + 1;
  const rx::Wearable& w = rx::wearables[slot];
  const int16_t y = ROW_TOP + slot * ROW_HEIGHT;
  const bool duplicate = w.duplicateSeen && now - w.duplicateMs < rx::DUPLICATE_SHOW_MS;

  char line[48];  // anything past LINE_CHARS is cut off at the canvas edge
  uint16_t colour;
  if (!w.seen) {
    snprintf(line, sizeof(line), "W%u --   waiting", id);
    colour = MUTED;
  } else {
    // Firmware version from the wearable's Hello; v?.? until one arrives
    // (wearables before v0.8 send it only at power-up).
    char version[10] = "v?.?";
    if (w.firmwareMajor || w.firmwareMinor) {
      snprintf(version, sizeof(version), "v%u.%u", w.firmwareMajor, w.firmwareMinor);
    }
    snprintf(line, sizeof(line), "W%u %s %-5s %-4s %3u x%u", id, version, modeName(w.mode),
             duplicate ? "DUP" : w.live ? "LIVE" : "LOST", w.ratePerSecond, w.lostPerSecond);
    colour = duplicate ? ACCENT_2 : w.live ? ACCENT : BAD;
  }
  startText(lineCanvas, ST77XX_BLACK);
  printText(lineCanvas, colour, line);
  sendText(lineCanvas, 2, y);

  const int accel[3] = {w.ax, w.ay, w.az};
  const int gyro[3] = {w.gx, w.gy, w.gz};
  for (int axis = 0; axis < 3; ++axis) {
    const int16_t x = 2 + axis * (BAR_WIDTH + BAR_GAP);
    drawBar(x, y + 10, w.seen ? accel[axis] : 0, ACCEL_FULL_SCALE, AXIS_COLOURS[axis]);
    drawBar(x, y + 10 + BAR_HEIGHT + 2, w.seen ? gyro[axis] : 0, GYRO_FULL_SCALE, AXIS_COLOURS[axis]);
  }

  // Activity bar, then the markers (hit direction or cal, S still, B button)
  // and the tilt: "fwd S B p-12 r  34".
  const int16_t detailY = y + 10 + 2 * (BAR_HEIGHT + 2);
  drawLevel(2, detailY + 1, w.hasMotion ? w.activity : 0, w.hit ? ACCENT_2 : ACCENT);
  startText(detailCanvas, ST77XX_BLACK);
  if (!w.seen) {
    // blank
  } else if (!w.hasMotion) {
    printText(detailCanvas, MUTED, "old fw: no tilt");
  } else {
    if (w.hit) {
      printText(detailCanvas, ACCENT_2, directionName(w.hitDirection));
    } else if (!w.gyroCalibrated) {
      printText(detailCanvas, ACCENT_2, "cal");
    } else {
      printText(detailCanvas, MUTED, "   ");
    }
    printText(detailCanvas, TEXT, w.still ? " S" : "  ");
    printText(detailCanvas, TEXT, w.button ? " B" : "  ");
    char tilt[24];
    snprintf(tilt, sizeof(tilt), " p%3d r%4d", w.pitch / 10, w.roll / 10);
    printText(detailCanvas, MUTED, tilt);
  }
  sendText(detailCanvas, DETAIL_X, detailY);
}

}  // namespace

void begin() {
  tft.initR(RX_TFT_TAB);
  tft.setSPISpeed(rx::TFT_SPI_HZ);
  tft.setRotation(1);
  tft.setTextWrap(false);
  drawSplash();
  delay(rx::DISPLAY_SPLASH_MS);
  tft.fillScreen(INK);
  tft.fillRect(0, 0, WIDTH, TITLE_HEIGHT, ACCENT);
  Serial.println("[display] ST7735 started (logo shown)");
  if (!lineCanvas.getBuffer() || !detailCanvas.getBuffer()) Serial.println("[display] no memory for text");
}

void update(uint32_t now) {
  if (!cycleRunning) {
    if (now - cycleStartMs < rx::DISPLAY_REFRESH_MS) return;
    cycleStartMs = now;
    cycleRunning = true;
    nextPiece = 0;
  }
  if (nextPiece == 0) {
    drawTitle(now);
  } else {
    drawRow(nextPiece - 1, now);
  }
  if (++nextPiece > rx::DISPLAY_SLOTS) cycleRunning = false;
}

}  // namespace display
