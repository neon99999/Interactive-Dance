#include "motion.h"

#include <Arduino.h>
#include <math.h>

#include "config.h"

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
uint32_t lastHitMs = 0;

float wrap180(float degrees) {
  while (degrees > 180.0f) degrees -= 360.0f;
  while (degrees < -180.0f) degrees += 360.0f;
  return degrees;
}

// Averages the gyro over GYRO_CALIBRATION_MS windows until one is still.
void calibrateGyro(const imu::Reading& r) {
  const float g[3] = {r.gx, r.gy, r.gz};
  if (windowCount == 0) {
    windowStartMs = r.timeMs;
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
  if (r.timeMs - windowStartMs < dance::GYRO_CALIBRATION_MS) return;

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

void updateTilt(const imu::Reading& r, float accelMagnitude, float dt) {
  const float gravityRoll = atan2f(r.ay, r.az) * DEGREES_PER_RADIAN;
  const float gravityPitch = atan2f(-r.ax, sqrtf(r.ay * r.ay + r.az * r.az)) * DEGREES_PER_RADIAN;
  const bool gravityTrusted = fabsf(accelMagnitude - 1.0f) < dance::TILT_GRAVITY_TOLERANCE_G;
  if (!tiltStarted) {
    if (!gravityTrusted) return;
    s.pitch = gravityPitch;
    s.roll = gravityRoll;
    tiltStarted = true;
    return;
  }
  // Follow the gyro, then pull a little towards gravity.
  s.roll = wrap180(s.roll + s.gx * dt);
  s.pitch = constrain(s.pitch + s.gy * dt, -90.0f, 90.0f);
  if (gravityTrusted && dt > 0) {
    const float k = dt / (dance::TILT_TIME_CONSTANT_S + dt);
    s.roll = wrap180(s.roll + k * wrap180(gravityRoll - s.roll));
    s.pitch += k * (gravityPitch - s.pitch);
  }
}

void updateActivity(float accelMagnitude, float dt) {
  const float linear = fabsf(accelMagnitude - 1.0f) / dance::ACTIVITY_FULL_ACCEL_G;
  const float spin = sqrtf(s.gx * s.gx + s.gy * s.gy + s.gz * s.gz) / dance::ACTIVITY_FULL_GYRO_DPS;
  const float target = fminf(1.0f, fmaxf(linear, spin));
  if (dt <= 0) return;
  const float timeConstant = target > s.activity ? dance::ACTIVITY_RISE_S : dance::ACTIVITY_FALL_S;
  s.activity += (target - s.activity) * (1.0f - expf(-dt / timeConstant));
}

void updateHit(float accelMagnitude, uint32_t nowMs) {
  const float excess = accelMagnitude - 1.0f;
  if (!hitArmed && excess < dance::HIT_THRESHOLD_G * 0.5f && nowMs - lastHitMs >= dance::HIT_REARM_MS) {
    hitArmed = true;
  }
  if (hitArmed && excess > dance::HIT_THRESHOLD_G) {
    hitArmed = false;
    anyHit = true;
    lastHitMs = nowMs;
    ++s.hits;
  }
  s.hit = anyHit && nowMs - lastHitMs < dance::HIT_HOLD_MS;
}

}  // namespace

void update(const imu::Reading& r) {
  if (!s.gyroCalibrated) calibrateGyro(r);
  s.gx = r.gx - bias[0];
  s.gy = r.gy - bias[1];
  s.gz = r.gz - bias[2];

  float dt = haveLastSample ? (r.timeUs - lastUs) * 1e-6f : 0.0f;
  if (dt > MAX_STEP_S) dt = 0;
  lastUs = r.timeUs;
  haveLastSample = true;

  const float accelMagnitude = sqrtf(r.ax * r.ax + r.ay * r.ay + r.az * r.az);
  updateTilt(r, accelMagnitude, dt);
  updateActivity(accelMagnitude, dt);
  updateHit(accelMagnitude, r.timeMs);
  ++s.samples;
}

const State& state() { return s; }

}  // namespace motion
