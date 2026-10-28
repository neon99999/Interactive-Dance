# Wearable sensor firmware

Firmware for the wireless wearable motion sensors used with the Interactive Dance TouchDesigner toolkit. Each wearable sends its movement over ESP-NOW to a receiver, which passes it on to TouchDesigner.

**Status:** architecture only. The wearable firmware boots, logs over USB serial and identifies itself. Every hardware module is a placeholder. It compiles; **nothing has been tested on hardware yet.**

## Hardware (per wearable)

- Seeed Studio XIAO ESP32-C6
- Adafruit LSM6DS3TR-C IMU (I2C)
- Pushbutton
- Vibration motor, switched by an NPN transistor
- LiPo battery, voltage read through a divider
- ESP-NOW to a receiver ESP32 (board not chosen yet)

## Structure

```
Firmware/
  platformio.ini        build environments (wearable only, for now)
  include/
    config.h            firmware version, wearable id, pins, IMU address, battery divider
    protocol.h          versioned ESP-NOW packet layout, shared by wearable and receiver
  src/
    wearable/
      main.cpp          boot, identity log, module start-up, main loop, heartbeat log
      imu.*             LSM6DS3TR-C (placeholder)
      espnow_link.*     ESP-NOW link to the receiver (placeholder)
      button.*          pushbutton (placeholder)
      haptic.*          vibration motor (holds the motor pin LOW; no patterns yet)
      battery.*         battery voltage (placeholder)
    receiver/
      main.cpp          placeholder; not built until the receiver board is confirmed
```

Each module has `begin()` and `update()`; `main.cpp` calls them, so a module is filled in without touching the others. `build_src_filter` keeps the wearable and receiver sources apart in one project.

## Building

Needs [PlatformIO Core](https://platformio.org/install/cli) (or the VS Code PlatformIO extension). From this folder:

```
pio run -e wearable                    # build
pio run -e wearable -t upload          # flash over USB
pio device monitor -b 115200           # serial log
```

The first build downloads the platform and toolchain (about 1 GB). On Windows, run it from PowerShell, cmd or VS Code, **not Git Bash**: the ESP-IDF tool installer refuses MSYS shells, which leaves the compiler uninstalled (`'riscv32-esp-elf-g++' is not recognized`). To give a wearable a different id without editing `config.h`, add `-D DANCE_WEARABLE_ID=2` to `build_flags`.

**Platform:** the official `espressif32` platform supports the XIAO ESP32-C6 only with ESP-IDF. For the Arduino framework this project uses the community [pioarduino](https://github.com/pioarduino/platform-espressif32) platform, pinned to release `55.03.312-1` (Arduino core 3.3.12, ESP-IDF 5.5.5). Change the version deliberately and on every machine at once.

## Expected serial output

```
Interactive Dance wearable v0.1
  wearable id 1, protocol v1
  chip ESP32-C6 rev ..., 160 MHz, efuse MAC ...
[imu] placeholder: LSM6DS3TR-C expected at 0x6A (SDA 22, SCL 23), not started
[button] placeholder: pin 1, not read
[battery] placeholder: ADC pin 0, divider x2.0, not read
[espnow] placeholder: protocol v1, not started
boot complete
[heartbeat] uptime 5 s
```

The `[haptic]` line prints before the serial port is open, so it is usually not shown.

## Protocol

`include/protocol.h` defines the packets. Every packet starts with a 6-byte header: magic `0xDA`, protocol version, packet type, wearable id and a sequence number. A receiver drops packets with an unknown magic or version. Any change to a packet's layout or meaning increments `PROTOCOL_VERSION`, and `static_assert`s on the struct sizes catch accidental layout changes at compile time. Only `Hello` is defined so far.

## Implemented vs. hardware-unverified

| Item | State |
|---|---|
| Builds for `seeed_xiao_esp32c6` with Arduino | Compiles with no warnings (MINI-PC, 2026-10-28): RAM 4.4%, flash 19.4% |
| Boot, USB serial log, identity, heartbeat | Written; **not run on a board** |
| Motor pin held LOW from boot | Written; **not checked on hardware** |
| IMU, ESP-NOW, button, battery | Placeholders only |
| Receiver | Source placeholder; no build target |
| Pin numbers in `config.h` | **Provisional**, not checked against the wiring |

To check on the hardware first:

1. Flash a wearable and confirm the serial output above, including after pressing reset (USB CDC serial on the C6).
2. Confirm the motor does not run at power-up or reset.
3. Check every pin in `config.h` against the actual wiring.
4. Confirm the IMU's I2C address (0x6A, or 0x6B if SDO/SA0 is high).
5. Measure the battery divider and set `BATTERY_DIVIDER_RATIO`.

## Decisions to revisit

- **Pins:** I2C on D4/D5 (the board's default I2C pins), button D1, motor D2, battery A0. The XIAO ESP32-C6 has no on-board battery voltage divider, so the battery needs an external one into A0.
- **Antenna:** the board support code (`initVariant`) turns on the RF switch (GPIO3 LOW) and selects the on-board antenna (GPIO14 LOW) at boot, so the firmware leaves those pins alone. For an external antenna, set GPIO14 HIGH after boot. Check ESP-NOW range on the real costume.
- **Receiver to TouchDesigner:** planned as serial lines in the `name=value` format the existing `inputs` component already reads (for example `w1_ax=0.12`). Nothing is fixed yet.
- **Wearable id:** set at build time for now. Flash storage or the MAC address may be easier with many wearables.
