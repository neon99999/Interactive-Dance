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
constexpr int16_t ROW_HEIGHT = 27;  // name line, accel bars, gyro bars
constexpr uint8_t MAX_ROWS = (HEIGHT - ROW_TOP) / ROW_HEIGHT;  // 4
constexpr int16_t BAR_WIDTH = 50;
constexpr int16_t BAR_HEIGHT = 6;
constexpr int16_t BAR_GAP = 3;
constexpr int ACCEL_FULL_SCALE = 2000;  // 2 g in protocol units fills a bar
constexpr int GYRO_FULL_SCALE = 5000;   // 500 dps

constexpr uint16_t GREY = 0x7BEF;
constexpr uint16_t DARK = 0x2104;
constexpr uint16_t TITLE_BG = 0x000F;  // dark blue
constexpr uint16_t AXIS_COLOURS[3] = {ST77XX_RED, ST77XX_GREEN, ST77XX_BLUE};

Adafruit_ST7735 tft(rx::PIN_TFT_CS, rx::PIN_TFT_DC, rx::PIN_TFT_RST);
uint32_t lastDrawMs = 0;
int shownRows = -1;  // rows on screen; -1 forces a full redraw

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

void drawText(int16_t x, int16_t y, uint16_t colour, const char* text) {
  tft.setTextColor(colour, ST77XX_BLACK);  // background colour overwrites old text
  tft.setCursor(x, y);
  tft.print(text);
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

void drawTitle(uint32_t now) {
  char line[27];
  snprintf(line, sizeof(line), "Dance RX  ch %u", dance::ESPNOW_CHANNEL);
  tft.setTextColor(ST77XX_WHITE, TITLE_BG);
  tft.setCursor(2, 2);
  tft.print(line);
  snprintf(line, sizeof(line), "%6lus", static_cast<unsigned long>(now / 1000));
  tft.setCursor(WIDTH - 2 - 7 * 6, 2);
  tft.print(line);
}

void drawWaiting() {
  char line[27];
  drawText(4, 40, ST77XX_WHITE, "Waiting for wearables");
  snprintf(line, sizeof(line), "channel %u, protocol v%u", dance::ESPNOW_CHANNEL, dance::PROTOCOL_VERSION);
  drawText(4, 56, GREY, line);
  snprintf(line, sizeof(line), "bad %lu  dropped %lu", static_cast<unsigned long>(rx::totals.badPackets),
           static_cast<unsigned long>(radio::droppedCount()));
  drawText(4, 72, GREY, line);
}

void drawRow(uint8_t row, uint8_t id, const rx::Wearable& w) {
  const int16_t y = ROW_TOP + row * ROW_HEIGHT;
  char line[27];
  snprintf(line, sizeof(line), "W%u %-4s %3u/s lost %-6lu", id, w.live ? "LIVE" : "LOST", w.ratePerSecond,
           static_cast<unsigned long>(w.lost));
  drawText(2, y, w.live ? ST77XX_GREEN : ST77XX_RED, line);
  const int accel[3] = {w.ax, w.ay, w.az};
  const int gyro[3] = {w.gx, w.gy, w.gz};
  for (int axis = 0; axis < 3; ++axis) {
    const int16_t x = 2 + axis * (BAR_WIDTH + BAR_GAP);
    drawBar(x, y + 10, accel[axis], ACCEL_FULL_SCALE, AXIS_COLOURS[axis]);
    drawBar(x, y + 10 + BAR_HEIGHT + 2, gyro[axis], GYRO_FULL_SCALE, AXIS_COLOURS[axis]);
  }
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
}

void update(uint32_t now) {
  if (now - lastDrawMs < rx::DISPLAY_REFRESH_MS) return;
  lastDrawMs = now;

  // The first MAX_ROWS wearables seen, in id order.
  uint8_t ids[MAX_ROWS];
  uint8_t rows = 0;
  for (uint8_t i = 0; i < rx::MAX_WEARABLES && rows < MAX_ROWS; ++i) {
    if (rx::wearables[i].seen) ids[rows++] = i + 1;
  }
  if (rows != shownRows) {  // layout changed: clear below the title
    tft.fillRect(0, TITLE_HEIGHT, WIDTH, HEIGHT - TITLE_HEIGHT, ST77XX_BLACK);
    shownRows = rows;
  }
  drawTitle(now);
  if (rows == 0) {
    drawWaiting();
    return;
  }
  for (uint8_t row = 0; row < rows; ++row) drawRow(row, ids[row], rx::wearables[ids[row] - 1]);
}

}  // namespace display
