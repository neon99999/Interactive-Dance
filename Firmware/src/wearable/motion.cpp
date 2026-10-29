#include "motion.h"

#include <Arduino.h>
#include <math.h>

#include "config.h"
#include "mode.h"

namespace motion {

namespace {

constexpr float DEGREES_PER_RADIAN = 57.29578f;
constexpr float MAX_STEP_S = 0.1f;  // a longer gap between samples is not integrated

State s = {};

// Gyro calibration window.
float bias[3] = {0, 0, 0};
float sum[3], low[3], high[3];
uint32_t windowCount = 0;
uint32_t windowStartMs = 0;
bool askedToHoldStill = false;

uint32_t lastUs = 0;
bool haveLastSample = false;
bool tiltStarted = false;

bool hitArmed = true;
bool anyHit = false;
uint32_t hitStartMs = 0;

bool quiet = false;
uint32_t quietSinceMs = 0;

float wrap180(float degrees) {
  while (degrees > 180.0f) degrees -= 360.0f;
  while (degrees < -180.0f) degrees += 360.0f;
  return degrees;
}

// One body axis from a sensor vector: +1/+2/+3 = sensor x/y/z, negative = reversed.
float bodyAxis(const float sensor[3], int8_t code) {
  return code > 0 ? sensor[code - 1] : -sensor[-code - 1];
}

// Averages the gyro over GYRO_CALIBRATION_MS windows until one is still.
void calibrateGyro(const float g[3], uint32_t nowMs) {
  if (windowCount == 0) {
    windowStartMs = nowMs;
    for (int i = 0; i < 3; ++i) {
      sum[i] = 0;
      low[i] = high[i] = g[i];
    }
  }
  for (int i = 0; i < 3; ++i) {
    sum[i] += g[i];
    low[i] = fminf(low[i], g[i]);
    high[i] = fmaxf(high[i], g[i]);
  }
  ++windowCount;
  if (nowMs - windowStartMs < dance::GYRO_CALIBRATION_MS) return;

  bool still = true;
  float mean[3];
  for (int i = 0; i < 3; ++i) {
    mean[i] = sum[i] / windowCount;
    if (high[i] - mean[i] > dance::GYRO_STILL_DPS || mean[i] - low[i] > dance::GYRO_STILL_DPS) still = false;
  }
  windowCount = 0;
  if (still) {
    for (int i = 0; i < 3; ++i) bias[i] = mean[i];
    s.gyroCalibrated = true;
    Serial.printf("[motion] gyro calibrated, bias %.2f %.2f %.2f dps\n", bias[0], bias[1], bias[2]);
  } else if (!askedToHoldStill) {
    askedToHoldStill = true;
    Serial.println("[motion] hold the wearable still for a second to calibrate the gyro");
  }
}

void updateTilt(float accelMagnitude, float dt) {
  const float gravityRoll = atan2f(s.ay, s.az) * DEGREES_PER_RADIAN;
  const float gravityPitch = atan2f(s.ax, sqrtf(s.ay * s.ay + s.az * s.az)) * DEGREES_PER_RADIAN;
  const bool gravityTrusted = fabsf(accelMagnitude - 1.0f) < dance::TILT_GRAVITY_TOLERANCE_G;
  if (!tiltStarted) {
    if (!gravityTrusted) return;
    s.pitch = gravityPitch;
    s.roll = gravityRoll;
    tiltStarted = true;
    return;
  }
  // Follow the gyro (turning about the left axis tips the forward end down),
  // then pull a little towards gravity.
  s.roll = wrap180(s.roll + s.gx * dt);
  s.pitch = constrain(s.pitch - s.gy * dt, -90.0f, 90.0f);
  if (gravityTrusted && dt > 0) {
    const float k = dt / (dance::TILT_TIME_CONSTANT_S + dt);
    s.roll = wrap180(s.roll + k * wrap180(gravityRoll - s.roll));
    s.pitch += k * (gravityPitch - s.pitch);
  }
}

dance::HitDirection directionOf(float x, float y, float z) {
  const float ax = fabsf(x), ay = fabsf(y), az = fabsf(z);
  if (ax >= ay && ax >= az) return x > 0 ? dance::HitDirection::Forward : dance::HitDirection::Back;
  if (ay >= az) return y > 0 ? dance::HitDirection::Left : dance::HitDirection::Right;
  return z > 0 ? dance::HitDirection::Up : dance::HitDirection::Down;
}

// The acceleration with gravity (from the tilt) taken away, then a hit when
// it passes the mode's threshold. Its direction is that of the first spike.
void updateHit(const dance::ModeSettings& m, uint32_t nowMs) {
  const float pitch = s.pitch / DEGREES_PER_RADIAN, roll = s.roll / DEGREES_PER_RADIAN;
  const float lx = s.ax - sinf(pitch);
  const float ly = s.ay - sinf(roll) * cosf(pitch);
  const float lz = s.az - cosf(roll) * cosf(pitch);
  const float size = sqrtf(lx * lx + ly * ly + lz * lz);
  if (!hitArmed && nowMs - hitStartMs >= dance::HIT_WINDOW_MS && size < m.hitThresholdG * 0.5f) hitArmed = true;
  if (hitArmed && size > m.hitThresholdG) {
    hitArmed = false;
    anyHit = true;
    hitStartMs = nowMs;
    s.hitDirection = directionOf(lx, ly, lz);
    ++s.hits;
  }
  s.hit = anyHit && nowMs - hitStartMs < dance::HIT_HOLD_MS;
}

// Movement: the larger of acceleration away from 1 g and rotation speed,
// each as a fraction of the mode's full scale.
float movement(const dance::ModeSettings& m, float accelMagnitude) {
  const float linear = fabsf(accelMagnitude - 1.0f) / m.fullAccelG;
  const float spin = sqrtf(s.gx * s.gx + s.gy * s.gy + s.gz * s.gz) / m.fullGyroDps;
  return fmaxf(linear, spin);
}

void updateActivity(float amount, float dt) {
  if (dt <= 0) return;
  const float target = fminf(1.0f, amount);
  const float timeConstant = target > s.activity ? dance::ACTIVITY_RISE_S : dance::ACTIVITY_FALL_S;
  s.activity += (target - s.activity) * (1.0f - expf(-dt / timeConstant));
}

void updateStill(const dance::ModeSettings& m, float amount, uint32_t nowMs) {
  if (amount < m.stillLevel) {
    if (!quiet) {
      quiet = true;
      quietSinceMs = nowMs;
    }
    if (nowMs - quietSinceMs >= dance::STILL_MS) s.still = true;
  } else {
    quiet = false;
    if (amount > 2.0f * m.stillLevel) s.still = false;
  }
}

}  // namespace

void update(const imu::Reading& r) {
  const float sensorAccel[3] = {r.ax, r.ay, r.az};
  const float sensorGyro[3] = {r.gx, r.gy, r.gz};
  s.ax = bodyAxis(sensorAccel, dance::BODY_FORWARD_AXIS);
  s.ay = bodyAxis(sensorAccel, dance::BODY_LEFT_AXIS);
  s.az = bodyAxis(sensorAccel, dance::BODY_UP_AXIS);
  float g[3] = {bodyAxis(sensorGyro, dance::BODY_FORWARD_AXIS), bodyAxis(sensorGyro, dance::BODY_LEFT_AXIS),
                bodyAxis(sensorGyro, dance::BODY_UP_AXIS)};
  if (!s.gyroCalibrated) calibrateGyro(g, r.timeMs);
  s.gx = g[0] - bias[0];
  s.gy = g[1] - bias[1];
  s.gz = g[2] - bias[2];

  float dt = haveLastSample ? (r.timeUs - lastUs) * 1e-6f : 0.0f;
  if (dt > MAX_STEP_S) dt = 0;
  lastUs = r.timeUs;
  haveLastSample = true;

  const dance::ModeSettings& m = mode::settings();
  const float accelMagnitude = sqrtf(s.ax * s.ax + s.ay * s.ay + s.az * s.az);
  updateTilt(accelMagnitude, dt);
  updateHit(m, r.timeMs);
  const float amount = movement(m, accelMagnitude);
  updateActivity(amount, dt);
  updateStill(m, amount, r.timeMs);
  ++s.samples;
}

const State& state() { return s; }

}  // namespace motion
