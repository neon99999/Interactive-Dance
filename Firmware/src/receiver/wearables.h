// What the receiver knows about each wearable, shared by main.cpp (which
// fills it from packets) and the display (which shows it).
#pragma once

#include <stdint.h>

#include "receiver_config.h"

namespace rx {

struct Wearable {
  bool seen = false;         // any valid packet since boot
  bool live = false;         // a packet within LOST_AFTER_MS
  uint32_t lastPacketMs = 0;
  uint16_t lastSequence = 0;
  uint32_t packets = 0;      // valid packets since boot
  uint32_t lost = 0;         // gaps in the sequence numbers
  uint16_t ratePerSecond = 0;
  uint16_t packetsThisSecond = 0;
  uint16_t lostPerSecond = 0;     // lost in the last full second
  uint16_t lostThisSecond = 0;
  uint8_t firmwareMajor = 0, firmwareMinor = 0;  // from Hello; 0.0 until one arrives
  uint8_t protocolVersion = 0;     // of the last packet
  uint8_t mac[6] = {};             // sender of the last packet
  uint32_t duplicateMs = 0;        // last packet from a second device with this id
  bool duplicateSeen = false;
  // protocol.h fixed point:
  int16_t ax = 0, ay = 0, az = 0;  // thousandths of a g
  int16_t gx = 0, gy = 0, gz = 0;  // tenths of a degree per second
  // Motion processing, protocol v3 (wearable fw v0.7) and later:
  bool hasMotion = false;
  int16_t pitch = 0, roll = 0;     // tenths of a degree
  uint16_t activity = 0;           // 0..MOTION_ACTIVITY_FULL
  bool hit = false;
  uint8_t hitDirection = 0;        // dance::HitDirection
  uint8_t hits = 0;
  bool still = false;
  bool button = false;
  bool gyroCalibrated = false;
  uint8_t mode = 0;                // dance::Mode, 0 = unknown
};

// Index 0 is wearable id 1.
extern Wearable wearables[MAX_WEARABLES];

struct Totals {
  uint32_t badPackets = 0;  // wrong magic, version, length or id
};

extern Totals totals;

}  // namespace rx
