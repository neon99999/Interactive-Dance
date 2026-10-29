// Build-time settings for the wearable firmware.
//
// PIN ASSIGNMENTS: the IMU's I2C pins (D4/D5) match the wiring. The button,
// motor and battery pins are still provisional; confirm them on the hardware.

#pragma once

#include <stdint.h>

namespace dance {

constexpr const char* FIRMWARE_NAME = "Interactive Dance wearable";
constexpr uint8_t FIRMWARE_VERSION_MAJOR = 0;
constexpr uint8_t FIRMWARE_VERSION_MINOR = 5;

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
constexpr int PIN_BUTTON = 1;        // D1, pushbutton to GND (internal pull-up planned)
constexpr int PIN_HAPTIC = 2;        // D2, base of the NPN transistor driving the motor
constexpr int PIN_BATTERY_ADC = 0;   // A0/D0, LiPo through an external voltage divider

// LSM6DS3TR-C I2C address: 0x6A, or 0x6B when its SDO/SA0 pin is high
// (the Adafruit breakout defaults to 0x6A).
// The firmware also tries the other address if this one does not answer.
constexpr uint8_t IMU_I2C_ADDRESS = 0x6A;
constexpr uint32_t I2C_CLOCK_HZ = 400000;
constexpr uint32_t IMU_READ_MS = 10;      // poll the sensor (it samples at 104 Hz)
constexpr uint32_t IMU_LOG_MS = 20;       // print a reading this often (50 Hz); 0 = never
constexpr uint32_t IMU_RETRY_MS = 3000;   // look for a missing sensor again

// Send a Motion packet over ESP-NOW at most this often (50 Hz). The channel is
// in protocol.h because the receiver must use the same one.
constexpr uint32_t ESPNOW_SEND_MS = 20;

// Battery voltage = ADC pin voltage * this ratio (2.0 for two equal resistors).
constexpr float BATTERY_DIVIDER_RATIO = 2.0f;

}  // namespace dance
