#include "button.h"

#include <Arduino.h>

#include "config.h"
#include "mode.h"

namespace button {

namespace {

bool pressed = false;        // debounced state
bool lastReading = false;
uint32_t readingSinceMs = 0;  // when the raw reading last changed
uint32_t pressedSinceMs = 0;
bool longPressHandled = false;

}  // namespace

bool begin() {
  pinMode(dance::PIN_BUTTON, INPUT_PULLUP);
  Serial.printf("[button] pin %d, pull-up; hold %.1f s to switch wrist/ankle\n", dance::PIN_BUTTON,
                dance::BUTTON_LONG_PRESS_MS / 1000.0f);
  return true;
}

void update() {
  const uint32_t now = millis();
  const bool reading = digitalRead(dance::PIN_BUTTON) == LOW;
  if (reading != lastReading) {
    lastReading = reading;
    readingSinceMs = now;
  }
  if (reading != pressed && now - readingSinceMs >= dance::BUTTON_DEBOUNCE_MS) {
    pressed = reading;
    if (pressed) {
      pressedSinceMs = now;
      longPressHandled = false;
    }
  }
  if (pressed && !longPressHandled && now - pressedSinceMs >= dance::BUTTON_LONG_PRESS_MS) {
    longPressHandled = true;
    mode::set(mode::current() == dance::Mode::Wrist ? dance::Mode::Ankle : dance::Mode::Wrist);
  }
}

bool isPressed() { return pressed; }

}  // namespace button
