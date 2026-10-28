#include "haptic.h"

#include <Arduino.h>

#include "config.h"

namespace haptic {

bool begin() {
  // Keep the transistor off so the motor cannot run while the rest is a placeholder.
  pinMode(dance::PIN_HAPTIC, OUTPUT);
  digitalWrite(dance::PIN_HAPTIC, LOW);
  Serial.printf("[haptic] placeholder: pin %d held LOW (motor off), no patterns yet\n", dance::PIN_HAPTIC);
  return true;
}

void update() {}

}  // namespace haptic
