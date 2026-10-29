// Pushbutton on PIN_BUTTON, wired to GND, with the internal pull-up.
// Debounced; isPressed() is sent to TouchDesigner as btn. Holding it for
// BUTTON_LONG_PRESS_MS switches the wearing mode (mode.h). With no button
// wired the pull-up keeps it released.
#pragma once

namespace button {
bool begin();
void update();
bool isPressed();
}  // namespace button
