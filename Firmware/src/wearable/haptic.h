// Vibration motor, switched by an NPN transistor on PIN_HAPTIC.
// begin() drives the pin LOW so the motor stays off from boot. Later: timed
// pulses and patterns, triggered from the receiver.
#pragma once

namespace haptic {
bool begin();
void update();
}  // namespace haptic
