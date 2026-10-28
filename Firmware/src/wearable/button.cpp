#include "button.h"

#include <Arduino.h>

#include "config.h"

namespace button {

bool begin() {
  Serial.printf("[button] placeholder: pin %d, not read\n", dance::PIN_BUTTON);
  return false;
}

void update() {}

}  // namespace button
