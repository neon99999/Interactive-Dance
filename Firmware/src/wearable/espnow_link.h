// ESP-NOW link to the receiver.
// Placeholder: begin() only logs. Later: start Wi-Fi in station mode, init
// ESP-NOW, add the receiver as a peer and send protocol.h packets.
#pragma once

namespace espnow_link {
bool begin();
void update();
}  // namespace espnow_link
