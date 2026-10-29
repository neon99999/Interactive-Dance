// Motion processing on the wearable, run on every IMU sample (208 Hz) so that
// short events are not missed between radio packets:
//   - body axes: the sensor axes turned to x forward, y left, z up (config.h)
//   - gyro bias, measured at boot while the wearable lies still
//   - tilt: pitch (forward end up = positive) and roll (rolled right =
//     positive), by a complementary filter
//   - activity, 0..1, how much the wearable is moving
//   - hit, a sharp acceleration with gravity removed, held on for
//     HIT_HOLD_MS, with the body direction of the first spike
//   - still, after STILL_MS of hardly any movement
// Thresholds come from the wearing mode (mode.h). Tools/motion_model.py is a
// Python copy of this file for tuning on recordings: change both together.
#pragma once

#include <stdint.h>

#include "imu.h"
#include "protocol.h"

namespace motion {

struct State {
  float ax, ay, az;     // acceleration in g, body axes
  float gx, gy, gz;     // rotation in degrees per second, body axes, gyro bias removed
  float pitch, roll;    // degrees; pitch -90..90, roll -180..180
  float activity;       // 0 still .. 1 at the mode's full movement or more
  bool hit;             // a hit started within the last HIT_HOLD_MS
  dance::HitDirection hitDirection;  // of the latest hit
  uint8_t hits;         // hits since boot, wraps at 255
  bool still;
  bool gyroCalibrated;  // false until the wearable has been still for GYRO_CALIBRATION_MS
  uint32_t samples;     // samples processed since boot
};

void update(const imu::Reading& reading);  // call once per new IMU sample
const State& state();

}  // namespace motion
