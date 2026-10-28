#include "battery.h"

#include <Arduino.h>

#include "config.h"

namespace battery {

bool begin() {
  Serial.printf("[battery] placeholder: ADC pin %d, divider x%.1f, not read\n",
                dance::PIN_BATTERY_ADC, dance::BATTERY_DIVIDER_RATIO);
  return false;
}

void update() {}

}  // namespace battery
