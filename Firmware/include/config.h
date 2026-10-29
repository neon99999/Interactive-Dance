// Build-time settings for the wearable firmware.
//
// PIN ASSIGNMENTS: the IMU's I2C pins (D4/D5) match the wiring. The button,
// motor and battery pins are still provisional; confirm them on the hardware.

#pragma once

#include <stdint.h>

namespace dance {

constexpr const char* FIRMWARE_NAME = "Interactive Dance wearable";
constexpr uint8_t FIRMWARE_VERSION_MAJOR = 0;
constexpr uint8_t FIRMWARE_VERSION_MINOR = 7;

constexpr uint32_t SERIAL_BAUD = 115200;
constexpr uint32_t SERIAL_WAIT_MS = 2000;     // wait this long for a USB serial monitor at boot
constexpr uint32_t HEARTBEAT_LOG_MS = 5000;   // "still alive" log interval

// Which dancer's wearable this is; sent in every packet. Set per device
// before flashing (later this may come from flash storage instead).
#ifndef DANCE_WEARABLE_ID
#define DANCE_WEARABLE_ID 1
#endif
constexpr uint8_t WEARABLE_ID = DANCE_WEARABLE_ID;

// --- Pins (XIAO ESP32-C6 label -> GPIO). See above. ---
constexpr int PIN_I2C_SDA = 22;      // D4, default I2C SDA, to the LSM6DS3TR-C
constexpr int PIN_I2C_SCL = 23;      // D5, default I2C SCL
constexpr int PIN_BUTTON = 1;        // D1, pushbutton to GND (internal pull-up)
constexpr int PIN_HAPTIC = 2;        // D2, base of the NPN transistor driving the motor
constexpr int PIN_BATTERY_ADC = 0;   // A0/D0, LiPo through an external voltage divider

// LSM6DS3TR-C I2C address: 0x6A, or 0x6B when its SDO/SA0 pin is high
// (the Adafruit breakout defaults to 0x6A).
// The firmware also tries the other address if this one does not answer.
constexpr uint8_t IMU_I2C_ADDRESS = 0x6A;
constexpr uint32_t I2C_CLOCK_HZ = 400000;
constexpr uint32_t IMU_READ_MS = 1;       // poll for a new sample (the sensor samples at 208 Hz)
constexpr uint32_t IMU_LOG_MS = 20;       // print a reading on USB this often (50 Hz); 0 = never
constexpr uint32_t IMU_RETRY_MS = 3000;   // look for a missing sensor again

// Send a Motion packet over ESP-NOW for every this-many new IMU samples:
// 2 of 208 Hz = 104 packets a second, about 10 ms apart. Lower latency costs
// radio and serial bandwidth: three wearables at 104 Hz use about 60% of the
// receiver's 921600 baud line. The channel is in protocol.h because the
// receiver must use the same one.
constexpr uint8_t ESPNOW_SEND_EVERY_SAMPLES = 2;

// --- Body axes. ---
// Wearing standard: chip side facing out, USB connector towards the hand
// (wrist) or the toes (ankle). Body axes: x forward (towards the USB), y left,
// z up (out of the chip face). Which sensor axis points which way depends on
// how the IMU board sits on the wearable: +1/+2/+3 = sensor +x/+y/+z,
// -1/-2/-3 = the opposite. Check with the hand test in README.md.
constexpr int8_t BODY_FORWARD_AXIS = +1;
constexpr int8_t BODY_LEFT_AXIS = +2;
constexpr int8_t BODY_UP_AXIS = +3;

// --- Motion processing (motion.cpp), run on every IMU sample. ---
// Gyro bias: measured at boot while the wearable lies still. It counts as
// still when no gyro axis strays more than GYRO_STILL_DPS from its average
// over GYRO_CALIBRATION_MS; until then the bias is 0 and it keeps trying.
constexpr uint32_t GYRO_CALIBRATION_MS = 1000;
constexpr float GYRO_STILL_DPS = 3.0f;
// Tilt: complementary filter. The gyro gives fast changes, gravity corrects
// the drift with this time constant. Gravity is trusted only while the
// acceleration is close to 1 g (not during a jump or a hit).
constexpr float TILT_TIME_CONSTANT_S = 0.5f;
constexpr float TILT_GRAVITY_TOLERANCE_G = 0.25f;
// Activity rises and falls with these time constants.
constexpr float ACTIVITY_RISE_S = 0.03f;
constexpr float ACTIVITY_FALL_S = 0.4f;
// Hit: the flag stays on for HIT_HOLD_MS so TouchDesigner, which reads once
// per frame, cannot miss it. A punch is a spike one way (speeding up) and
// often one the other way (stopping): everything within HIT_WINDOW_MS is one
// hit, and a new one also needs the acceleration to fall below half the
// threshold first.
constexpr uint32_t HIT_HOLD_MS = 120;
constexpr uint32_t HIT_WINDOW_MS = 250;
// Still: movement below the mode's stillLevel for STILL_MS; it ends when
// movement goes above twice stillLevel.
constexpr uint32_t STILL_MS = 500;

// Per wearing mode. STARTING VALUES, not yet tuned on a body.
//   fullAccelG, fullGyroDps: movement at which activity reaches 1
//   hitThresholdG: acceleration (gravity removed) that counts as a hit
//   stillLevel: movement, as a fraction of full, below which the wearer is still
struct ModeSettings {
  const char* name;
  float fullAccelG;
  float fullGyroDps;
  float hitThresholdG;
  float stillLevel;
};
constexpr ModeSettings WRIST_SETTINGS = {"wrist", 1.5f, 600.0f, 1.5f, 0.04f};
// Ankles take a jolt at every step, so hits need a harder stamp or kick.
constexpr ModeSettings ANKLE_SETTINGS = {"ankle", 2.5f, 500.0f, 3.0f, 0.04f};

// --- Button and mode. ---
// Holding the button this long switches between wrist and ankle mode; the
// motor then buzzes once for wrist, twice for ankle. The mode is kept in
// flash. Over USB serial, typing w or a sets it too.
constexpr uint32_t BUTTON_DEBOUNCE_MS = 30;
constexpr uint32_t BUTTON_LONG_PRESS_MS = 1500;
constexpr uint32_t HAPTIC_BUZZ_MS = 150;  // one buzz, and the gap between buzzes

// Battery voltage = ADC pin voltage * this ratio (2.0 for two equal resistors).
constexpr float BATTERY_DIVIDER_RATIO = 2.0f;

}  // namespace dance
