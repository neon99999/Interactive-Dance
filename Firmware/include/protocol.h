// Packets exchanged between the wearables and the receiver over ESP-NOW.
//
// Shared by the wearable and receiver firmware, so both sides always agree on
// the layout. Every packet starts with PacketHeader; a receiver drops any
// packet whose magic or version it does not recognise.
//
// Rules for changing this file:
//   - Any change to a packet layout or meaning increments PROTOCOL_VERSION.
//   - Packets are packed little-endian structs, at most ESPNOW_MAX_PAYLOAD
//     bytes. ESP32 and ESP8266 are both little-endian, so the bytes are the
//     same on either receiver. Copy a received packet into a local struct
//     (memcpy) before reading it; the radio buffer may be unaligned.
//
// Defined so far: Hello and Motion. Button, battery and haptic packets come
// with the features that need them.

#pragma once

#include <stddef.h>
#include <stdint.h>

namespace dance {

constexpr uint8_t PROTOCOL_MAGIC = 0xDA;
constexpr uint8_t PROTOCOL_VERSION = 2;

// ESP-NOW v1 payload limit; keeps packets readable by ESP8266 and every ESP32.
constexpr size_t ESPNOW_MAX_PAYLOAD = 250;

// Wi-Fi channel (1-13) every wearable and the receiver use. ESP-NOW only
// reaches devices on the same channel. Change it on all devices at once, e.g.
// to move away from a busy Wi-Fi network at the venue.
constexpr uint8_t ESPNOW_CHANNEL = 1;

enum class PacketType : uint8_t {
  Hello = 1,   // wearable -> receiver: "I am here", sent at boot
  Motion = 2,  // wearable -> receiver: one IMU reading
  // Reserved for later: Button = 3, Battery = 4, Haptic = 5
};

#pragma pack(push, 1)

struct PacketHeader {
  uint8_t magic;       // PROTOCOL_MAGIC
  uint8_t version;     // PROTOCOL_VERSION
  uint8_t type;        // PacketType
  uint8_t wearableId;  // which dancer's wearable (config.h)
  uint16_t sequence;   // increments per packet sent; wraps at 65535
};

struct HelloPacket {
  PacketHeader header;
  uint8_t firmwareMajor;
  uint8_t firmwareMinor;
};

// Fixed-point so the packet stays small: accel in thousandths of a g
// (+-4 g fits easily), gyro in tenths of a degree per second (+-2000 dps).
constexpr float MOTION_ACCEL_PER_UNIT = 0.001f;
constexpr float MOTION_GYRO_PER_UNIT = 0.1f;

struct MotionPacket {
  PacketHeader header;
  int16_t ax, ay, az;  // x MOTION_ACCEL_PER_UNIT = g
  int16_t gx, gy, gz;  // x MOTION_GYRO_PER_UNIT = degrees per second
};

#pragma pack(pop)

static_assert(sizeof(PacketHeader) == 6, "PacketHeader layout changed: bump PROTOCOL_VERSION");
static_assert(sizeof(HelloPacket) == 8, "HelloPacket layout changed: bump PROTOCOL_VERSION");
static_assert(sizeof(MotionPacket) == 18, "MotionPacket layout changed: bump PROTOCOL_VERSION");
static_assert(sizeof(MotionPacket) <= ESPNOW_MAX_PAYLOAD, "packet too large for ESP-NOW");

inline PacketHeader makeHeader(PacketType type, uint8_t wearableId, uint16_t sequence) {
  return PacketHeader{PROTOCOL_MAGIC, PROTOCOL_VERSION, static_cast<uint8_t>(type), wearableId, sequence};
}

inline bool isValidHeader(const PacketHeader& header) {
  return header.magic == PROTOCOL_MAGIC && header.version == PROTOCOL_VERSION;
}

}  // namespace dance
