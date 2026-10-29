// ESP-NOW receive side. The only board-specific part of the receiver:
// radio_esp8266.cpp implements it for the NodeMCU. A later ESP32 receiver
// needs only its own radio_esp32.cpp with the same functions.
//
// Packets arrive in the radio's callback and wait in a small queue; pop()
// hands them to the main loop, so no printing happens inside the callback.
#pragma once

#include <stdint.h>

namespace radio {

constexpr uint8_t MAX_STORED_BYTES = 32;  // larger packets keep their length but are cut here

struct RawPacket {
  uint8_t mac[6];
  uint8_t length;  // length as received
  uint8_t data[MAX_STORED_BYTES];
};

bool begin(uint8_t channel);
bool pop(RawPacket& packet);
uint32_t droppedCount();  // packets lost because the queue was full

}  // namespace radio
