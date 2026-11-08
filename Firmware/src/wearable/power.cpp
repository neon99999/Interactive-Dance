#include "power.h"

#include <Arduino.h>
#include <esp_sleep.h>

#include "battery.h"
#include "config.h"
#include "espnow_link.h"
#include "haptic.h"
#include "imu.h"

namespace power {

namespace {

using dance::BatteryState;

BatteryState current = BatteryState::NoReading;
uint32_t lastCheckMs = 0;
bool critical = false;        // the shutdown condition holds; timing it
uint32_t criticalSinceMs = 0;
bool startedLowOnUsb = false;  // started below BATTERY_START_MILLIVOLTS with a computer connected

// Ok / Low / NoReading from the smoothed voltage, with a little hysteresis on Low.
BatteryState levelFor(uint16_t millivolts, BatteryState previous) {
  if (millivolts == 0) return BatteryState::NoReading;
  if (millivolts <= dance::BATTERY_LOW_MILLIVOLTS) return BatteryState::Low;
  if (previous == BatteryState::Low && millivolts <= dance::BATTERY_LOW_CLEAR_MILLIVOLTS) return BatteryState::Low;
  return BatteryState::Ok;
}

// USB counts only for a real reading: a simulated voltage must be testable at the desk.
bool usbExempt() { return usbComputer() && !battery::isSimulated(); }

[[noreturn]] void shutDown(bool notify) {
  current = BatteryState::ShuttingDown;
  if (notify) {
    for (uint8_t i = 0; i < dance::POWER_NOTICE_REPEATS; ++i) {
      espnow_link::sendBatteryStatus();
      delay(dance::POWER_NOTICE_GAP_MS);  // broadcasts are not acknowledged: send a few, let each go out
    }
  }
  imu::powerDown();
  haptic::powerDown();
  espnow_link::end();
  Serial.println("[power] deep sleep with no wake-up. Charge, then press RESET (or switch off and on).");
  delay(50);  // let the last USB line out if a computer is listening
  esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_ALL);
  esp_deep_sleep_start();
}

}  // namespace

void checkAtBoot() {
  const uint16_t millivolts = battery::millivolts();
  current = levelFor(millivolts, BatteryState::NoReading);
  if (millivolts == 0) {
    Serial.println("[power] no battery reading: low-battery protection cannot act");
    return;
  }
  if (millivolts >= dance::BATTERY_START_MILLIVOLTS) {
    Serial.printf("[power] battery %u mV: ok to start (needs %u)\n", millivolts, dance::BATTERY_START_MILLIVOLTS);
    return;
  }
  // Too low to start on the battery. A computer may still be enumerating: look for a moment.
  const uint32_t start = millis();
  while (!usbExempt() && !battery::isSimulated() && millis() - start < dance::USB_DETECT_MS) delay(10);
  if (usbExempt()) {
    startedLowOnUsb = true;
    Serial.printf("[power] battery %u mV, below %u, but a USB computer is connected: running on USB. "
                  "Unplugged before it charges to %u, it shuts down.\n",
                  millivolts, dance::BATTERY_START_MILLIVOLTS, dance::BATTERY_START_MILLIVOLTS);
    return;
  }
  Serial.printf("[power] battery %u mV, below %u needed to start: not starting\n", millivolts,
                dance::BATTERY_START_MILLIVOLTS);
  shutDown(espnow_link::isReady());  // at boot the radio is not up yet, so no notice
}

void update() {
  const uint32_t now = millis();
  if (now - lastCheckMs < dance::POWER_CHECK_MS) return;
  lastCheckMs = now;

  const uint16_t millivolts = battery::millivolts();
  const BatteryState next = levelFor(millivolts, current);
  if (next != current) {
    Serial.printf("[power] battery %s (%u mV)\n", stateName(next), millivolts);
    current = next;
    espnow_link::sendBatteryStatus();
  }

  if (usbExempt()) {
    // Running from USB: nothing to protect. Charged enough, the start rule is satisfied too.
    if (startedLowOnUsb && millivolts >= dance::BATTERY_START_MILLIVOLTS) {
      startedLowOnUsb = false;
      Serial.printf("[power] charged to %u mV: may now run on the battery\n", millivolts);
    }
    critical = false;
    return;
  }
  const bool tooLow = millivolts != 0 && (millivolts <= dance::BATTERY_CRITICAL_MILLIVOLTS ||
                                          (startedLowOnUsb && millivolts < dance::BATTERY_START_MILLIVOLTS));
  if (!tooLow) {
    if (critical) Serial.printf("[power] battery back to %u mV: no shutdown\n", millivolts);
    critical = false;
    return;
  }
  if (!critical) {
    critical = true;
    criticalSinceMs = now;
    Serial.printf("[power] battery %u mV: shutting down in %lu s unless it recovers\n", millivolts,
                  static_cast<unsigned long>(dance::BATTERY_CRITICAL_MS / 1000));
    return;
  }
  if (now - criticalSinceMs >= dance::BATTERY_CRITICAL_MS) {
    Serial.printf("[power] battery %u mV for %lu s: shutting down\n", millivolts,
                  static_cast<unsigned long>(dance::BATTERY_CRITICAL_MS / 1000));
    shutDown(true);
  }
}

BatteryState state() { return current; }

bool usbComputer() { return HWCDC::isPlugged(); }

const char* stateName(BatteryState state) {
  switch (state) {
    case BatteryState::Ok: return "ok";
    case BatteryState::Low: return "LOW";
    case BatteryState::ShuttingDown: return "shutting down";
    case BatteryState::NoReading: break;
  }
  return "no reading";
}

}  // namespace power
