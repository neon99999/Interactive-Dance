#include "espnow_link.h"

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <math.h>

#include "config.h"
#include "imu.h"
#include "motion.h"
#include "protocol.h"

namespace espnow_link {

namespace {

const uint8_t BROADCAST_ADDRESS[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

bool ready = false;
uint16_t sequence = 0;
uint32_t sent = 0;
uint32_t failed = 0;
uint32_t lastSentSample = 0;

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

void sendMotion(const imu::Reading& r, const motion::State& m) {
  uint8_t flags = 0;
  if (m.hit) flags |= dance::MOTION_FLAG_HIT;
  if (m.gyroCalibrated) flags |= dance::MOTION_FLAG_GYRO_CALIBRATED;
  dance::MotionPacket packet{dance::makeHeader(dance::PacketType::Motion, dance::WEARABLE_ID, sequence++),
                             toFixed(r.ax, dance::MOTION_ACCEL_PER_UNIT),
                             toFixed(r.ay, dance::MOTION_ACCEL_PER_UNIT),
                             toFixed(r.az, dance::MOTION_ACCEL_PER_UNIT),
                             toFixed(m.gx, dance::MOTION_GYRO_PER_UNIT),
                             toFixed(m.gy, dance::MOTION_GYRO_PER_UNIT),
                             toFixed(m.gz, dance::MOTION_GYRO_PER_UNIT),
                             toFixed(m.pitch, dance::MOTION_ANGLE_PER_UNIT),
                             toFixed(m.roll, dance::MOTION_ANGLE_PER_UNIT),
                             static_cast<uint16_t>(lroundf(constrain(m.activity, 0.0f, 1.0f) *
                                                           dance::MOTION_ACTIVITY_FULL)),
                             flags,
                             m.hits};
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
  const motion::State& m = motion::state();
  if (m.samples - lastSentSample < dance::ESPNOW_SEND_EVERY_SAMPLES) return;
  lastSentSample = m.samples;
  sendMotion(imu::latest(), m);
}

bool isReady() { return ready; }

uint32_t sentCount() { return sent; }

uint32_t failedCount() { return failed; }

}  // namespace espnow_link
