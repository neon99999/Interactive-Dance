// Packets exchanged between the wearables and the receiver over ESP-NOW.
//
// Shared by the wearable and receiver firmware, so both sides always agree on
// the layout. Every packet starts with PacketHeader; a receiver drops any
// packet whose magic or version it does not recognise.
//
// Rules for changing this file:
//   - Any change to a packet layout or meaning increments PROTOCOL_VERSION.
//   - Packets are packed little-endian structs (ESP32 byte order), at most
//     ESPNOW_MAX_PAYLOAD bytes.
//
// Only the header and the hello packet are defined so far; motion, button and
// haptic packets come with the features that need them.

#pragma once

#include <stddef.h>
#include <stdint.h>

namespace dance {

constexpr uint8_t PROTOCOL_MAGIC = 0xDA;
constexpr uint8_t PROTOCOL_VERSION = 1;

// ESP-NOW v1 payload limit; keeps packets compatible with every ESP32 receiver.
constexpr size_t ESPNOW_MAX_PAYLOAD = 250;

enum class PacketType : uint8_t {
  Hello = 1,  // wearable -> receiver: "I am here", sent at boot
  // Reserved for later: Motion = 2, Button = 3, Battery = 4, Haptic = 5
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

#pragma pack(pop)

static_assert(sizeof(PacketHeader) == 6, "PacketHeader layout changed: bump PROTOCOL_VERSION");
static_assert(sizeof(HelloPacket) == 8, "HelloPacket layout changed: bump PROTOCOL_VERSION");
static_assert(sizeof(HelloPacket) <= ESPNOW_MAX_PAYLOAD, "packet too large for ESP-NOW");

inline PacketHeader makeHeader(PacketType type, uint8_t wearableId, uint16_t sequence) {
  return PacketHeader{PROTOCOL_MAGIC, PROTOCOL_VERSION, static_cast<uint8_t>(type), wearableId, sequence};
}

inline bool isValidHeader(const PacketHeader& header) {
  return header.magic == PROTOCOL_MAGIC && header.version == PROTOCOL_VERSION;
}

}  // namespace dance
