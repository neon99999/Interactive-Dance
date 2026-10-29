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
  uint8_t firmwareMajor = 0, firmwareMinor = 0;  // from Hello; 0.0 until one arrives
  int16_t ax = 0, ay = 0, az = 0;  // protocol.h fixed point (thousandths of a g)
  int16_t gx = 0, gy = 0, gz = 0;  // tenths of a degree per second
};

// Index 0 is wearable id 1.
extern Wearable wearables[MAX_WEARABLES];

struct Totals {
  uint32_t badPackets = 0;  // wrong magic, version, length or id
};

extern Totals totals;

}  // namespace rx
