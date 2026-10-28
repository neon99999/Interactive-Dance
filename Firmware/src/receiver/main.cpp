// Receiver firmware: placeholder.
//
// Not built yet: platformio.ini has no [env:receiver] until the receiver board
// is confirmed. The receiver will listen for protocol.h packets over ESP-NOW
// and forward them to TouchDesigner (most likely as serial lines the existing
// inputs component already reads, e.g. "w1_ax=0.12").

#include <Arduino.h>

#include "protocol.h"

void setup() {
  Serial.begin(115200);
  Serial.printf("Interactive Dance receiver placeholder, protocol v%u\n", dance::PROTOCOL_VERSION);
}

void loop() { delay(1000); }
