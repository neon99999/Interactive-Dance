#include "mode.h"

#include <Arduino.h>
#include <Preferences.h>

#include "haptic.h"

namespace mode {

namespace {

constexpr const char* STORAGE_NAMESPACE = "dance";
constexpr const char* STORAGE_KEY = "mode";

dance::Mode currentMode = dance::Mode::Wrist;

}  // namespace

void begin() {
  Preferences storage;
  if (storage.begin(STORAGE_NAMESPACE, true)) {
    const uint8_t saved = storage.getUChar(STORAGE_KEY, static_cast<uint8_t>(dance::Mode::Wrist));
    if (saved == static_cast<uint8_t>(dance::Mode::Ankle)) currentMode = dance::Mode::Ankle;
    storage.end();
  }
  Serial.printf("[mode] %s (hold the button or type w / a to change)\n", settings().name);
}

dance::Mode current() { return currentMode; }

const dance::ModeSettings& settings() {
  return currentMode == dance::Mode::Ankle ? dance::ANKLE_SETTINGS : dance::WRIST_SETTINGS;
}

void set(dance::Mode mode) {
  if (mode != currentMode) {
    currentMode = mode;
    Preferences storage;
    if (storage.begin(STORAGE_NAMESPACE, false)) {
      storage.putUChar(STORAGE_KEY, static_cast<uint8_t>(mode));
      storage.end();
    }
  }
  Serial.printf("[mode] %s\n", settings().name);
  haptic::buzz(mode == dance::Mode::Ankle ? 2 : 1);
}

}  // namespace mode
