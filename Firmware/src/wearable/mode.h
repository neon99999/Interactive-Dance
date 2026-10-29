// Wearing mode: wrist or ankle. Picks the motion thresholds (config.h), is
// sent in every Motion packet and kept in flash across power-offs. Changed
// by a long button press or by typing w or a over USB serial.
#pragma once

#include "config.h"
#include "protocol.h"

namespace mode {

void begin();  // loads the saved mode (wrist the first time)
dance::Mode current();
const dance::ModeSettings& settings();
void set(dance::Mode mode);  // saves it, logs it and buzzes 1 (wrist) or 2 (ankle) times

}  // namespace mode
