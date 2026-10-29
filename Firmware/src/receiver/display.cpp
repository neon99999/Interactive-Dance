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
constexpr int16_t DETAIL_X = 2 + BAR_WIDTH + BAR_GAP + 2;  // tilt text, right of the activity bar
constexpr int16_t DETAIL_CHARS = (WIDTH - DETAIL_X) / 6;

static_assert(ROW_TOP + rx::DISPLAY_SLOTS * ROW_HEIGHT <= HEIGHT, "wearable rows do not fit on the screen");

constexpr uint16_t GREY = 0x7BEF;
constexpr uint16_t DARK = 0x2104;
constexpr uint16_t ORANGE = 0xFD20;
constexpr uint16_t TITLE_BG = 0x000F;  // dark blue
constexpr uint16_t AXIS_COLOURS[3] = {ST77XX_RED, ST77XX_GREEN, ST77XX_BLUE};

Adafruit_ST7735 tft(rx::PIN_TFT_CS, rx::PIN_TFT_DC, rx::PIN_TFT_RST);

// Text is drawn into these off-screen buffers and sent to the display in one
// block. Printing straight to the display sends every pixel on its own,
// which takes about 15 ms a line and would hold back the serial output.
GFXcanvas16 lineCanvas(LINE_CHARS * 6, 8);
GFXcanvas16 detailCanvas(DETAIL_CHARS * 6, 8);

uint32_t cycleStartMs = 0;
uint8_t nextPiece = 0;  // 0 = title, 1..DISPLAY_SLOTS = a wearable's row
bool cycleRunning = false;

// Colour test card: four labelled stripes. Red must be on the left; if it
// shows blue, change RX_TFT_TAB in receiver_config.h.
void drawTestCard() {
  const uint16_t colours[4] = {ST77XX_RED, ST77XX_GREEN, ST77XX_BLUE, ST77XX_WHITE};
  const char* labels[4] = {"R", "G", "B", "W"};
  for (int i = 0; i < 4; ++i) {
    tft.fillRect(i * WIDTH / 4, 0, WIDTH / 4, HEIGHT, colours[i]);
    tft.setTextColor(i == 3 ? ST77XX_BLACK : ST77XX_WHITE);
    tft.setTextSize(2);
    tft.setCursor(i * WIDTH / 4 + 14, HEIGHT / 2 - 8);
    tft.print(labels[i]);
  }
  tft.drawRect(0, 0, WIDTH, HEIGHT, ST77XX_YELLOW);  // all four edges must show
  tft.setTextSize(1);
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
  tft.fillRect(x, y, from - x, BAR_HEIGHT, DARK);
  tft.fillRect(from, y, to - from, BAR_HEIGHT, colour);
  tft.fillRect(to, y, x + BAR_WIDTH - to, BAR_HEIGHT, DARK);
  tft.drawFastVLine(centre, y, BAR_HEIGHT, GREY);
}

// A bar filling from the left, for activity 0..MOTION_ACTIVITY_FULL.
void drawLevel(int16_t x, int16_t y, int value, uint16_t colour) {
  const int16_t length = static_cast<int16_t>(constrain(static_cast<long>(value) * BAR_WIDTH /
                                                        dance::MOTION_ACTIVITY_FULL, 0, BAR_WIDTH));
  tft.fillRect(x, y, length, BAR_HEIGHT, colour);
  tft.fillRect(x + length, y, BAR_WIDTH - length, BAR_HEIGHT, DARK);
}

void drawTitle(uint32_t now) {
  // Wearables beyond the rows on screen still reach TouchDesigner; count them.
  uint8_t others = 0;
  for (uint8_t i = rx::DISPLAY_SLOTS; i < rx::MAX_WEARABLES; ++i) others += rx::wearables[i].live ? 1 : 0;
  char line[48];  // anything past LINE_CHARS is cut off at the canvas edge
  char extra[8] = "";
  if (others) snprintf(extra, sizeof(extra), " +%u", others);
  snprintf(line, sizeof(line), "Dance RX ch %u%-5s%7lus", dance::ESPNOW_CHANNEL, extra,
           static_cast<unsigned long>(now / 1000));
  startText(lineCanvas, TITLE_BG);
  printText(lineCanvas, ST77XX_WHITE, line);
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
    colour = GREY;
  } else {
    snprintf(line, sizeof(line), "W%u %-4s %3u/s lost %-6lu", id, duplicate ? "DUP" : w.live ? "LIVE" : "LOST",
             w.ratePerSecond, static_cast<unsigned long>(w.lost));
    colour = duplicate ? ST77XX_YELLOW : w.live ? ST77XX_GREEN : ST77XX_RED;
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

  // Activity bar, then the hit or calibration marker and the tilt.
  const int16_t detailY = y + 10 + 2 * (BAR_HEIGHT + 2);
  drawLevel(2, detailY + 1, w.hasMotion ? w.activity : 0, w.hit ? ST77XX_YELLOW : ST77XX_WHITE);
  startText(detailCanvas, ST77XX_BLACK);
  if (!w.seen) {
    // blank
  } else if (!w.hasMotion) {
    printText(detailCanvas, GREY, "old fw: no tilt");
  } else {
    if (w.hit) {
      printText(detailCanvas, ST77XX_YELLOW, "HIT");
    } else if (!w.gyroCalibrated) {
      printText(detailCanvas, ORANGE, "cal");
    } else {
      printText(detailCanvas, GREY, "   ");
    }
    char tilt[DETAIL_CHARS + 1];
    snprintf(tilt, sizeof(tilt), " p%4d r%4d", w.pitch / 10, w.roll / 10);
    printText(detailCanvas, GREY, tilt);
  }
  sendText(detailCanvas, DETAIL_X, detailY);
}

}  // namespace

void begin() {
  tft.initR(RX_TFT_TAB);
  tft.setSPISpeed(rx::TFT_SPI_HZ);
  tft.setRotation(1);
  tft.setTextWrap(false);
  drawTestCard();
  delay(rx::DISPLAY_TEST_MS);
  tft.fillScreen(ST77XX_BLACK);
  tft.fillRect(0, 0, WIDTH, TITLE_HEIGHT, TITLE_BG);
  Serial.println("[display] ST7735 started (test card shown)");
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
