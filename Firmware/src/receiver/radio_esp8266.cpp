#ifdef ESP8266

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <espnow.h>

#include "radio.h"

namespace radio {

namespace {

constexpr uint8_t QUEUE_SIZE = 32;

RawPacket queue[QUEUE_SIZE];
volatile uint8_t head = 0;  // written by the callback
volatile uint8_t tail = 0;  // written by pop()
volatile uint32_t dropped = 0;

void onReceive(uint8_t* mac, uint8_t* data, uint8_t length) {
  const uint8_t next = (head + 1) % QUEUE_SIZE;
  if (next == tail) {
    ++dropped;
    return;
  }
  RawPacket& slot = queue[head];
  memcpy(slot.mac, mac, sizeof(slot.mac));
  slot.length = length;
  memcpy(slot.data, data, length < MAX_STORED_BYTES ? length : MAX_STORED_BYTES);
  head = next;
}

}  // namespace

bool begin(uint8_t channel) {
  WiFi.persistent(false);  // do not write Wi-Fi settings to flash
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  if (!wifi_set_channel(channel)) {
    Serial.printf("[radio] could not set channel %u\n", channel);
    return false;
  }
  if (esp_now_init() != 0) {
    Serial.println("[radio] ESP-NOW init failed");
    return false;
  }
  esp_now_set_self_role(ESP_NOW_ROLE_SLAVE);
  esp_now_register_recv_cb(onReceive);
  Serial.printf("[radio] listening on channel %u, MAC %s\n", channel, WiFi.macAddress().c_str());
  return true;
}

bool pop(RawPacket& packet) {
  noInterrupts();
  const bool empty = tail == head;
  if (!empty) {
    packet = queue[tail];
    tail = (tail + 1) % QUEUE_SIZE;
  }
  interrupts();
  return !empty;
}

uint32_t droppedCount() { return dropped; }

}  // namespace radio

#endif  // ESP8266
