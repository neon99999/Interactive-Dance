# Wearable sensor firmware

Firmware for the wireless wearable motion sensors used with the Interactive Dance TouchDesigner toolkit. Each wearable sends its movement over ESP-NOW to a receiver, which passes it on to TouchDesigner.

**Status:** the wearable boots, logs over USB serial, identifies itself and reads the IMU (accelerometer and gyroscope), sending 50 readings a second over USB serial. The button, motor, battery and ESP-NOW modules are still placeholders. The IMU readings were checked on a board with v0.2 (values follow tilting and turning).

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
      imu.*             LSM6DS3TR-C, read directly over I2C (no library)
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
Interactive Dance wearable v0.3
  wearable id 1, protocol v1
  chip ESP32-C6 rev ..., 160 MHz, efuse MAC ...
[imu] I2C on SDA 22, SCL 23
[imu] I2C devices: 0x6A
[imu] LSM6DS3TR-C ready at 0x6A: 104 Hz, +-4 g, +-2000 dps
[button] placeholder: pin 1, not read
[battery] placeholder: ADC pin 0, divider x2.0, not read
[espnow] placeholder: protocol v1, not started
boot complete
ax=0.012 ay=-0.021 az=1.003 gx=0.4 gy=-0.3 gz=0.1
...
[heartbeat] uptime 5 s, wearable 1, fw v0.3, imu ok at 0x6A
```

The boot lines are usually printed before the serial monitor has opened (the board resets after flashing and the USB port reconnects), so often only the later lines show. **Type any key in the monitor** to print the identity again; the heartbeat line also shows the firmware version and the IMU state. The `[haptic]` line always prints too early to be seen.

Readings are `name=value` lines: `ax ay az` in g, `gx gy gz` in degrees per second. TouchDesigner's `inputs` component reads them over USB serial (Read Serial on, 115200) as `serial_ax` ... `serial_gz`, and `imu_monitor` graphs them. Log lines start with `[` so TouchDesigner ignores them. Close the PlatformIO monitor first: only one program can open the port.

Lying flat and still, the IMU should read about 1 g on one axis and close to 0 on the others, with the gyro near 0. If it says `not found`, the scan line lists what is on the I2C bus: `none` means a wiring or power problem; the firmware keeps looking every 3 s, so a wire can be fixed without a reset.

## Protocol

`include/protocol.h` defines the packets. Every packet starts with a 6-byte header: magic `0xDA`, protocol version, packet type, wearable id and a sequence number. A receiver drops packets with an unknown magic or version. Any change to a packet's layout or meaning increments `PROTOCOL_VERSION`, and `static_assert`s on the struct sizes catch accidental layout changes at compile time. Only `Hello` is defined so far.

## Implemented vs. hardware-unverified

| Item | State |
|---|---|
| Builds for `seeed_xiao_esp32c6` with Arduino | Compiles with no warnings (MINI-PC, 2026-10-28): RAM 4.8%, flash 22.2% |
| Boot, USB serial log, heartbeat | Runs on a board (heartbeat seen in the monitor) |
| Motor pin held LOW from boot | Written; **not checked on hardware** |
| IMU detection and readings | v0.2 run on a board: found at 0x6A, about 1 g at rest, values follow tilting and turning |
| v0.3 `name=value` output at 50 Hz, read by TouchDesigner | Compiles; TouchDesigner side tested with simulated lines; **not yet run with the board** |
| ESP-NOW, button, battery | Placeholders only |
| Receiver | Source placeholder; no build target |
| Pin numbers in `config.h` | IMU on D4/D5 matches the wiring; button, motor, battery **provisional** |

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
