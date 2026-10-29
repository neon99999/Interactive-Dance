#include "espnow_link.h"

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <math.h>

#include "config.h"
#include "imu.h"
#include "protocol.h"

namespace espnow_link {

namespace {

const uint8_t BROADCAST_ADDRESS[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

bool ready = false;
uint16_t sequence = 0;
uint32_t sent = 0;
uint32_t failed = 0;
uint32_t lastSendMs = 0;
uint32_t lastSentReadingMs = 0;

int16_t toFixed(float value, float perUnit) {
  const float units = roundf(value / perUnit);
  return static_cast<int16_t>(constrain(units, -32768.0f, 32767.0f));
}

void send(const void* packet, size_t size) {
  if (esp_now_send(BROADCAST_ADDRESS, static_cast<const uint8_t*>(packet), size) == ESP_OK) {
    ++sent;
  } else {
    ++failed;
  }
}

void sendHello() {
  dance::HelloPacket packet{dance::makeHeader(dance::PacketType::Hello, dance::WEARABLE_ID, sequence++),
                            dance::FIRMWARE_VERSION_MAJOR, dance::FIRMWARE_VERSION_MINOR};
  send(&packet, sizeof(packet));
}

void sendMotion(const imu::Reading& r) {
  dance::MotionPacket packet{dance::makeHeader(dance::PacketType::Motion, dance::WEARABLE_ID, sequence++),
                             toFixed(r.ax, dance::MOTION_ACCEL_PER_UNIT),
                             toFixed(r.ay, dance::MOTION_ACCEL_PER_UNIT),
                             toFixed(r.az, dance::MOTION_ACCEL_PER_UNIT),
                             toFixed(r.gx, dance::MOTION_GYRO_PER_UNIT),
                             toFixed(r.gy, dance::MOTION_GYRO_PER_UNIT),
                             toFixed(r.gz, dance::MOTION_GYRO_PER_UNIT)};
  send(&packet, sizeof(packet));
}

}  // namespace

bool begin() {
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  if (esp_wifi_set_channel(dance::ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE) != ESP_OK) {
    Serial.printf("[espnow] could not set channel %u\n", dance::ESPNOW_CHANNEL);
    return false;
  }
  if (esp_now_init() != ESP_OK) {
    Serial.println("[espnow] init failed");
    return false;
  }
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BROADCAST_ADDRESS, sizeof(BROADCAST_ADDRESS));
  peer.channel = dance::ESPNOW_CHANNEL;
  peer.ifidx = WIFI_IF_STA;
  peer.encrypt = false;
  if (esp_now_add_peer(&peer) != ESP_OK) {
    Serial.println("[espnow] could not add the broadcast peer");
    return false;
  }
  ready = true;
  Serial.printf("[espnow] broadcasting on channel %u, protocol v%u, MAC %s\n", dance::ESPNOW_CHANNEL,
                dance::PROTOCOL_VERSION, WiFi.macAddress().c_str());
  sendHello();
  return true;
}

void update() {
  if (!ready || !imu::isReady()) return;
  const imu::Reading& reading = imu::latest();
  if (reading.timeMs == 0 || reading.timeMs == lastSentReadingMs) return;  // nothing new
  const uint32_t now = millis();
  if (now - lastSendMs < dance::ESPNOW_SEND_MS) return;
  lastSendMs = now;
  lastSentReadingMs = reading.timeMs;
  sendMotion(reading);
}

bool isReady() { return ready; }

uint32_t sentCount() { return sent; }

uint32_t failedCount() { return failed; }

}  // namespace espnow_link
