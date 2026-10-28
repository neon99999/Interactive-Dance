#include "espnow_link.h"

#include <Arduino.h>

#include "protocol.h"

namespace espnow_link {

bool begin() {
  Serial.printf("[espnow] placeholder: protocol v%u, not started\n", dance::PROTOCOL_VERSION);
  return false;
}

void update() {}

}  // namespace espnow_link
