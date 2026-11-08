#include "haptic.h"

#include <Arduino.h>
#include <driver/gpio.h>

#include "config.h"

namespace haptic {

namespace {

uint8_t stepsLeft = 0;  // on and off steps still to run: two per buzz
uint32_t stepStartMs = 0;

void setMotor(bool on) { digitalWrite(dance::PIN_HAPTIC, on ? HIGH : LOW); }

}  // namespace

bool begin() {
  // Keep the transistor off so the motor cannot run at boot.
  pinMode(dance::PIN_HAPTIC, OUTPUT);
  setMotor(false);
  // Release the hold powerDown() set before a deep sleep; the pin is already LOW.
  gpio_hold_dis(static_cast<gpio_num_t>(dance::PIN_HAPTIC));
  Serial.printf("[haptic] pin %d, motor off\n", dance::PIN_HAPTIC);
  return true;
}

void buzz(uint8_t count) {
  stepsLeft = count * 2;
  stepStartMs = millis();
  setMotor(stepsLeft > 0);
}

void update() {
  if (stepsLeft == 0 || millis() - stepStartMs < dance::HAPTIC_BUZZ_MS) return;
  stepStartMs = millis();
  --stepsLeft;
  setMotor(stepsLeft % 2 == 0 && stepsLeft > 0);
}

void powerDown() {
  stepsLeft = 0;
  setMotor(false);
  gpio_hold_en(static_cast<gpio_num_t>(dance::PIN_HAPTIC));  // on the C6 this holds through deep sleep
}

}  // namespace haptic
