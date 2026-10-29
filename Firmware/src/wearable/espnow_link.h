// ESP-NOW link to the receiver.
// begin() starts Wi-Fi in station mode on ESPNOW_CHANNEL (protocol.h) and
// sends a Hello; update() broadcasts a Motion packet (the IMU reading plus the
// motion processing) every ESPNOW_SEND_EVERY_SAMPLES new samples. Broadcast
// needs no receiver address, so any receiver on the channel picks the packets up.
#pragma once

#include <stdint.h>

namespace espnow_link {

bool begin();
void update();

bool isReady();
uint32_t sentCount();    // packets handed to the radio
uint32_t failedCount();  // packets the radio refused to queue

}  // namespace espnow_link
