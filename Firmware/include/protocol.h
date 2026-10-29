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
//
// History: v2 Motion carried the raw IMU reading only (MotionPacketV2, kept so
// a receiver still reads wearables on fw v0.4-v0.5). v3 adds the wearable's
// motion processing: tilt, activity, hit with direction, still, the button
// and the wearing mode, all on the body axes (config.h).

#pragma once

#include <stddef.h>
#include <stdint.h>

namespace dance {

constexpr uint8_t PROTOCOL_MAGIC = 0xDA;
constexpr uint8_t PROTOCOL_VERSION = 3;
constexpr uint8_t PROTOCOL_VERSION_OLDEST = 2;  // oldest version a receiver still accepts

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

// Where the wearable is worn. Each mode has its own thresholds (config.h).
enum class Mode : uint8_t { Wrist = 1, Ankle = 2 };

// Direction of a hit along the body axes: forward is towards the USB
// connector (the hand or the toes), up is out of the chip face, left and
// right as seen looking down on the chip face with the USB pointing away.
enum class HitDirection : uint8_t { None = 0, Forward = 1, Back = 2, Up = 3, Down = 4, Left = 5, Right = 6 };

// Fixed-point so the packet stays small: accel in thousandths of a g
// (+-8 g fits easily), gyro in tenths of a degree per second (+-2000 dps).
constexpr float MOTION_ACCEL_PER_UNIT = 0.001f;
constexpr float MOTION_GYRO_PER_UNIT = 0.1f;

constexpr float MOTION_ANGLE_PER_UNIT = 0.1f;       // tilt in tenths of a degree
constexpr uint16_t MOTION_ACTIVITY_FULL = 1000;     // activity 0..1000 = 0..1
constexpr uint8_t MOTION_FLAG_HIT = 0x01;           // a hit started within the last HIT_HOLD_MS
constexpr uint8_t MOTION_FLAG_STILL = 0x02;         // held still for STILL_MS
constexpr uint8_t MOTION_FLAG_BUTTON = 0x04;        // button held down
constexpr uint8_t MOTION_FLAG_GYRO_CALIBRATED = 0x08;

// v2 layout: raw reading only.
struct MotionPacketV2 {
  PacketHeader header;
  int16_t ax, ay, az;  // x MOTION_ACCEL_PER_UNIT = g
  int16_t gx, gy, gz;  // x MOTION_GYRO_PER_UNIT = degrees per second
};

// v3. Axes are the body axes: x forward, y left, z up.
struct MotionPacket {
  PacketHeader header;
  int16_t ax, ay, az;     // x MOTION_ACCEL_PER_UNIT = g
  int16_t gx, gy, gz;     // x MOTION_GYRO_PER_UNIT = degrees per second, gyro bias removed
  int16_t pitch, roll;    // x MOTION_ANGLE_PER_UNIT = degrees of tilt from gravity
  uint16_t activity;      // 0..MOTION_ACTIVITY_FULL, how much the wearable is moving
  uint8_t flags;          // MOTION_FLAG_*
  uint8_t hitDirection;   // HitDirection of the latest hit, None before the first
  uint8_t hits;           // hits counted since boot, wraps at 255
  uint8_t mode;           // Mode
};

#pragma pack(pop)

static_assert(sizeof(PacketHeader) == 6, "PacketHeader layout changed: bump PROTOCOL_VERSION");
static_assert(sizeof(HelloPacket) == 8, "HelloPacket layout changed: bump PROTOCOL_VERSION");
static_assert(sizeof(MotionPacketV2) == 18, "MotionPacketV2 is a fixed old layout");
static_assert(sizeof(MotionPacket) == 28, "MotionPacket layout changed: bump PROTOCOL_VERSION");
static_assert(sizeof(MotionPacket) <= ESPNOW_MAX_PAYLOAD, "packet too large for ESP-NOW");

inline PacketHeader makeHeader(PacketType type, uint8_t wearableId, uint16_t sequence) {
  return PacketHeader{PROTOCOL_MAGIC, PROTOCOL_VERSION, static_cast<uint8_t>(type), wearableId, sequence};
}

inline bool isValidHeader(const PacketHeader& header) {
  return header.magic == PROTOCOL_MAGIC && header.version >= PROTOCOL_VERSION_OLDEST &&
         header.version <= PROTOCOL_VERSION;
}

}  // namespace dance
