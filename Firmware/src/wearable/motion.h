// Motion processing on the wearable, run on every IMU sample (208 Hz) so that
// short events are not missed between radio packets:
//   - gyro bias, measured at boot while the wearable lies still
//   - tilt (pitch and roll from gravity), by a complementary filter
//   - activity, 0..1, how much the wearable is moving
//   - hits, sharp accelerations, held on for HIT_HOLD_MS
// All settings are in config.h. Axes are the sensor's own: roll turns about x,
// pitch about y, both 0 when the sensor lies flat with z up. Roll is
// unreliable when pitch is near +-90 degrees.
#pragma once

#include <stdint.h>

#include "imu.h"

namespace motion {

struct State {
  float gx, gy, gz;     // rotation in degrees per second, gyro bias removed
  float pitch, roll;    // degrees; pitch -90..90, roll -180..180
  float activity;       // 0 still .. 1 at ACTIVITY_FULL_* or more
  bool hit;             // a hit within the last HIT_HOLD_MS
  uint8_t hits;         // hits since boot, wraps at 255
  bool gyroCalibrated;  // false until the wearable has been still for GYRO_CALIBRATION_MS
  uint32_t samples;     // samples processed since boot
};

void update(const imu::Reading& reading);  // call once per new IMU sample
const State& state();

}  // namespace motion
