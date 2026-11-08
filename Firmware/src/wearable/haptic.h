// Vibration motor, switched by an NPN transistor on PIN_HAPTIC.
// begin() drives the pin LOW so the motor stays off from boot. buzz(n) gives
// n short buzzes without blocking the loop; update() runs them. powerDown()
// switches the motor off and holds the pin LOW through deep sleep (an
// unheld pin could float and half-switch the transistor).
#pragma once

#include <stdint.h>

namespace haptic {
bool begin();
void update();
void buzz(uint8_t count);
void powerDown();
}  // namespace haptic
