#include "battery.h"

#include <Arduino.h>

#include "config.h"

namespace battery {

namespace {

struct CurvePoint {
  uint16_t millivolts;
  uint8_t percent;
};

// A typical LiPo at rest, with straight lines between the points. Rough: the
// voltage sags under load, and the curve differs from cell to cell.
constexpr CurvePoint CURVE[] = {{3300, 0},  {3500, 5},  {3600, 10}, {3700, 20}, {3800, 40},
                                {3900, 60}, {4000, 80}, {4100, 90}, {4200, 100}};
constexpr size_t CURVE_POINTS = sizeof(CURVE) / sizeof(CURVE[0]);

float smoothed = 0.0f;  // millivolts at the battery
uint32_t lastReadMs = 0;

float readBatteryMillivolts() {
  return analogReadMilliVolts(dance::PIN_BATTERY_ADC) * dance::BATTERY_DIVIDER_RATIO;
}

uint8_t percentFromMillivolts(uint16_t value) {
  if (value <= CURVE[0].millivolts) return 0;
  for (size_t i = 1; i < CURVE_POINTS; ++i) {
    const CurvePoint& low = CURVE[i - 1];
    const CurvePoint& high = CURVE[i];
    if (value < high.millivolts) {
      return low.percent + static_cast<uint32_t>(value - low.millivolts) * (high.percent - low.percent) /
                               (high.millivolts - low.millivolts);
    }
  }
  return 100;
}

}  // namespace

bool begin() {
  float total = 0.0f;
  for (uint8_t i = 0; i < dance::BATTERY_START_READS; ++i) total += readBatteryMillivolts();
  smoothed = total / dance::BATTERY_START_READS;
  lastReadMs = millis();
  if (hasReading()) {
    Serial.printf("[battery] %u mV, about %u%% (ADC pin %d, divider x%.1f)\n", millivolts(), percent(),
                  dance::PIN_BATTERY_ADC, dance::BATTERY_DIVIDER_RATIO);
  } else {
    Serial.printf("[battery] no reading on ADC pin %d (%.0f mV): is the divider wired?\n", dance::PIN_BATTERY_ADC,
                  smoothed);
  }
  return hasReading();
}

void update() {
  const uint32_t now = millis();
  if (now - lastReadMs < dance::BATTERY_READ_MS) return;
  lastReadMs = now;
  smoothed += (readBatteryMillivolts() - smoothed) * dance::BATTERY_SMOOTHING;
}

bool hasReading() { return smoothed >= dance::BATTERY_MIN_MILLIVOLTS && smoothed <= dance::BATTERY_MAX_MILLIVOLTS; }

uint16_t millivolts() { return hasReading() ? static_cast<uint16_t>(smoothed) : 0; }

uint8_t percent() { return hasReading() ? percentFromMillivolts(millivolts()) : 0; }

}  // namespace battery
