// Receiver firmware entry point (LOLIN NodeMCU V3, ESP8266).
//
// Listens for protocol.h packets over ESP-NOW and forwards each wearable's
// motion to TouchDesigner as one serial line of name=value pairs:
//   w1_ax=0.012 w1_ay=-0.021 w1_az=1.003 w1_gx=0.4 w1_gy=-0.3 w1_gz=0.1
// which inputs > Serial reads as serial_w1_ax ... serial_w1_gz. When a wearable
// appears or goes quiet it also prints w1_live=1 or w1_live=0. Log lines start
// with [ so TouchDesigner ignores them. The display shows the same state.

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <stdlib.h>
#include <string.h>

#include "display.h"
#include "protocol.h"
#include "radio.h"
#include "receiver_config.h"
#include "wearables.h"

namespace rx {
Wearable wearables[MAX_WEARABLES];
Totals totals;
}  // namespace rx

namespace {

uint32_t lastSecondMs = 0;
uint32_t lastHeartbeatMs = 0;

void logIdentity() {
  Serial.println();
  Serial.printf("[rx] %s v%u.%u, protocol v%u, channel %u\n", rx::FIRMWARE_NAME, rx::FIRMWARE_VERSION_MAJOR,
                rx::FIRMWARE_VERSION_MINOR, dance::PROTOCOL_VERSION, dance::ESPNOW_CHANNEL);
  Serial.printf("[rx] chip ESP8266 id %06X, %u MHz, MAC %s\n", ESP.getChipId(), ESP.getCpuFreqMHz(),
                WiFi.macAddress().c_str());
}

// Any key typed in a serial monitor prints the identity again (the boot log
// is usually gone by the time a monitor opens).
void replayIdentityOnKeypress() {
  if (!Serial.available()) return;
  while (Serial.available()) Serial.read();
  logIdentity();
}

// Appends "w<id>_<name>=<value> " with a fixed-point value, e.g. 1003 with 3
// decimals -> 1.003. Integer formatting only, so no printf float support is needed.
char* appendValue(char* out, uint8_t id, const char* name, int value, int decimals) {
  const unsigned scale = decimals == 3 ? 1000 : 10;
  const unsigned magnitude = static_cast<unsigned>(abs(value));
  return out + sprintf(out, "w%u_%s=%s%u.%0*u ", id, name, value < 0 ? "-" : "", magnitude / scale, decimals,
                       magnitude % scale);
}

void printMotion(uint8_t id, const rx::Wearable& w) {
  char line[128];
  char* p = line;
  p = appendValue(p, id, "ax", w.ax, 3);
  p = appendValue(p, id, "ay", w.ay, 3);
  p = appendValue(p, id, "az", w.az, 3);
  p = appendValue(p, id, "gx", w.gx, 1);
  p = appendValue(p, id, "gy", w.gy, 1);
  p = appendValue(p, id, "gz", w.gz, 1);
  p[-1] = '\n';  // replaces the last trailing space
  Serial.write(line, p - line);
}

void setLive(uint8_t id, rx::Wearable& w, bool live) {
  if (w.live == live) return;
  w.live = live;
  Serial.printf("w%u_live=%u\n", id, live ? 1 : 0);
  Serial.printf("[rx] wearable %u %s\n", id, live ? "connected" : "lost");
}

void handlePacket(const radio::RawPacket& raw, uint32_t now) {
  dance::PacketHeader header;
  if (raw.length < sizeof(header)) {
    ++rx::totals.badPackets;
    return;
  }
  memcpy(&header, raw.data, sizeof(header));
  if (!dance::isValidHeader(header) || header.wearableId < 1 || header.wearableId > rx::MAX_WEARABLES) {
    ++rx::totals.badPackets;
    return;
  }
  const uint8_t id = header.wearableId;
  rx::Wearable& w = rx::wearables[id - 1];

  const auto type = static_cast<dance::PacketType>(header.type);
  if (type == dance::PacketType::Hello && raw.length == sizeof(dance::HelloPacket)) {
    dance::HelloPacket hello;
    memcpy(&hello, raw.data, sizeof(hello));
    w.firmwareMajor = hello.firmwareMajor;
    w.firmwareMinor = hello.firmwareMinor;
    Serial.printf("[rx] wearable %u says hello: fw v%u.%u, MAC %02X:%02X:%02X:%02X:%02X:%02X\n", id,
                  hello.firmwareMajor, hello.firmwareMinor, raw.mac[0], raw.mac[1], raw.mac[2], raw.mac[3],
                  raw.mac[4], raw.mac[5]);
  } else if (type == dance::PacketType::Motion && raw.length == sizeof(dance::MotionPacket)) {
    dance::MotionPacket motion;
    memcpy(&motion, raw.data, sizeof(motion));
    w.ax = motion.ax;
    w.ay = motion.ay;
    w.az = motion.az;
    w.gx = motion.gx;
    w.gy = motion.gy;
    w.gz = motion.gz;
  } else {
    ++rx::totals.badPackets;
    return;
  }

  // Count gaps in the sequence. A big jump means the wearable restarted.
  const uint16_t gap = header.sequence - w.lastSequence;
  if (w.seen && gap > 1 && gap < 1000) w.lost += gap - 1;
  w.seen = true;
  w.lastSequence = header.sequence;
  w.lastPacketMs = now;
  ++w.packets;
  ++w.packetsThisSecond;
  setLive(id, w, true);
  if (type == dance::PacketType::Motion) printMotion(id, w);
}

void everySecond(uint32_t now) {
  if (now - lastSecondMs < 1000) return;
  lastSecondMs = now;
  for (uint8_t i = 0; i < rx::MAX_WEARABLES; ++i) {
    rx::Wearable& w = rx::wearables[i];
    w.ratePerSecond = w.packetsThisSecond;
    w.packetsThisSecond = 0;
    if (w.live && now - w.lastPacketMs > rx::LOST_AFTER_MS) setLive(i + 1, w, false);
  }
}

void logHeartbeat(uint32_t now) {
  if (now - lastHeartbeatMs < rx::HEARTBEAT_LOG_MS) return;
  lastHeartbeatMs = now;
  Serial.printf("[heartbeat] uptime %lu s, rx fw v%u.%u, channel %u, bad %lu, dropped %lu",
                static_cast<unsigned long>(now / 1000),
                rx::FIRMWARE_VERSION_MAJOR, rx::FIRMWARE_VERSION_MINOR, dance::ESPNOW_CHANNEL,
                static_cast<unsigned long>(rx::totals.badPackets), static_cast<unsigned long>(radio::droppedCount()));
  for (uint8_t i = 0; i < rx::MAX_WEARABLES; ++i) {
    const rx::Wearable& w = rx::wearables[i];
    if (!w.seen) continue;
    Serial.printf(", w%u %s %u/s lost %lu", i + 1, w.live ? "live" : "LOST", w.ratePerSecond,
                  static_cast<unsigned long>(w.lost));
  }
  Serial.println();
}

}  // namespace

void setup() {
  Serial.begin(rx::SERIAL_BAUD);
  delay(100);
  logIdentity();
  display::begin();
  if (!radio::begin(dance::ESPNOW_CHANNEL)) Serial.println("[rx] radio failed to start; nothing will be received");
  Serial.println("[rx] boot complete");
}

void loop() {
  const uint32_t now = millis();
  radio::RawPacket raw;
  while (radio::pop(raw)) handlePacket(raw, now);
  everySecond(now);
  display::update(now);
  logHeartbeat(now);
  replayIdentityOnKeypress();
  yield();
}
