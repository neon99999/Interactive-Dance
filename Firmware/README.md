# Wearable sensor firmware

Firmware for the wireless wearable motion sensors used with the Interactive Dance TouchDesigner toolkit. Each wearable sends its movement over ESP-NOW to a receiver, which passes it on to TouchDesigner.

**Status:** the wearable (v0.4) reads the IMU and sends 50 readings a second both over USB serial and by ESP-NOW radio. The receiver (v0.1, an ESP8266 NodeMCU) forwards the radio packets to TouchDesigner over USB and shows status on a small display. USB serial into TouchDesigner is verified on hardware; **the radio link and the receiver have only been compiled, not run on boards yet.** The button, motor and battery modules are still placeholders.

## Hardware (per wearable)

- Seeed Studio XIAO ESP32-C6
- Adafruit LSM6DS3TR-C IMU (I2C)
- Pushbutton
- Vibration motor, switched by an NPN transistor
- LiPo battery, voltage read through a divider
- ESP-NOW to the receiver

## Hardware (receiver)

- NodeMCU 1.0 (ESP-12E), ESP8266 (Arduino IDE board setting "NodeMCU 1.0 (ESP-12E Module)", PlatformIO `nodemcuv2`)
- Optional 1.8" 128x160 colour TFT, ST7735 controller, on SPI:

| Display pin | NodeMCU pin |
|---|---|
| VCC | 3V3 |
| GND | G |
| SCL | D5 (GPIO14) |
| SDA | D7 (GPIO13) |
| CS | D2 (GPIO4) |
| DC | D1 (GPIO5) |
| RES | D6 (GPIO12) |
| BL | 3V3 |

D3, D4 and D8 are boot-mode pins on the ESP8266; the display stays off them. Without a display the receiver works the same.

## Structure

```
Firmware/
  platformio.ini        build environments: wearable, receiver
  include/
    config.h            firmware version, wearable id, pins, IMU address, battery divider
    protocol.h          versioned ESP-NOW packet layout, shared by wearable and receiver
  src/
    wearable/
      main.cpp          boot, identity log, module start-up, main loop, heartbeat log
      imu.*             LSM6DS3TR-C, read directly over I2C (no library)
      espnow_link.*     ESP-NOW broadcast of Hello and Motion packets
      button.*          pushbutton (placeholder)
      haptic.*          vibration motor (holds the motor pin LOW; no patterns yet)
      battery.*         battery voltage (placeholder)
    receiver/
      main.cpp          packets in, serial lines out, wearable tracking, heartbeat log
      receiver_config.h version, serial speed, display pins and variant
      radio.h           ESP-NOW receive queue (the only board-specific interface)
      radio_esp8266.cpp its ESP8266 implementation; an ESP32 receiver adds radio_esp32.cpp
      wearables.h       per-wearable state shared with the display
      display.*         ST7735 status screen
```

Each module has `begin()` and `update()`; `main.cpp` calls them, so a module is filled in without touching the others. `build_src_filter` keeps the wearable and receiver sources apart in one project.

## Building

Needs [PlatformIO Core](https://platformio.org/install/cli) (or the VS Code PlatformIO extension). From this folder:

```
pio run -e wearable                    # build
pio run -e wearable -t upload          # flash over USB
pio device monitor -b 115200           # serial log
pio run -e receiver -t upload          # flash the receiver (NodeMCU)
pio device monitor -b 921600           # receiver log
```

The first build downloads the platform and toolchain (about 1 GB). On Windows, run it from PowerShell, cmd or VS Code, **not Git Bash**: the ESP-IDF tool installer refuses MSYS shells, which leaves the compiler uninstalled (`'riscv32-esp-elf-g++' is not recognized`). To give a wearable a different id without editing `config.h`, add `-D DANCE_WEARABLE_ID=2` to `build_flags`.

**Platform:** the official `espressif32` platform supports the XIAO ESP32-C6 only with ESP-IDF. For the Arduino framework this project uses the community [pioarduino](https://github.com/pioarduino/platform-espressif32) platform, pinned to release `55.03.312-1` (Arduino core 3.3.12, ESP-IDF 5.5.5). Change the version deliberately and on every machine at once.

## Expected serial output

```
Interactive Dance wearable v0.4
  wearable id 1, protocol v2
  chip ESP32-C6 rev ..., 160 MHz, efuse MAC ...
[imu] I2C on SDA 22, SCL 23
[imu] I2C devices: 0x6A
[imu] LSM6DS3TR-C ready at 0x6A: 104 Hz, +-4 g, +-2000 dps
[button] placeholder: pin 1, not read
[battery] placeholder: ADC pin 0, divider x2.0, not read
[espnow] broadcasting on channel 1, protocol v2, MAC ...
boot complete
ax=0.012 ay=-0.021 az=1.003 gx=0.4 gy=-0.3 gz=0.1
...
[heartbeat] uptime 5 s, wearable 1, fw v0.4, imu ok at 0x6A, espnow sent 250 failed 0
```

The boot lines are usually printed before the serial monitor has opened (the board resets after flashing and the USB port reconnects), so often only the later lines show. **Type any key in the monitor** to print the identity again; the heartbeat line also shows the firmware version and the IMU state. The `[haptic]` line always prints too early to be seen.

Readings are `name=value` lines: `ax ay az` in g, `gx gy gz` in degrees per second. TouchDesigner's `inputs` component reads them over USB serial (Read Serial on, 115200) as `serial_ax` ... `serial_gz`, and `imu_monitor` graphs them. Log lines start with `[` so TouchDesigner ignores them. Close the PlatformIO monitor first: only one program can open the port.

Lying flat and still, the IMU should read about 1 g on one axis and close to 0 on the others, with the gyro near 0. If it says `not found`, the scan line lists what is on the I2C bus: `none` means a wiring or power problem; the firmware keeps looking every 3 s, so a wire can be fixed without a reset.

## Receiver

The receiver listens on ESP-NOW channel 1 and prints one line per Motion packet, at 921600 baud:

```
w1_ax=0.012 w1_ay=-0.021 w1_az=1.003 w1_gx=0.4 w1_gy=-0.3 w1_gz=0.1
```

In TouchDesigner (**inputs > Serial**: Read Serial on, the receiver's port, **Baud Rate 921600**) these become `serial_w1_ax` ... `serial_w1_gz`; to graph wearable 1, set imu_monitor's **Signal Prefix** to `serial_w1_`. When a wearable appears or stays silent for a second the receiver prints `w1_live=1` or `w1_live=0`. Log lines (`[rx] ...`, `[heartbeat] ...` every 5 s with packet rate and losses per wearable) start with `[`.

The display first shows a colour test card for 1.5 s: red, green, blue and white stripes left to right, with a yellow frame on all four edges. If red and blue are swapped or an edge shows noise, change `RX_TFT_TAB` in `receiver_config.h`. Then it shows one row per wearable: LIVE or LOST, packets per second, lost packets, and bars for acceleration (top) and rotation (bottom), x red, y green, z blue.

## Protocol

`include/protocol.h` defines the packets. Every packet starts with a 6-byte header: magic `0xDA`, protocol version, packet type, wearable id and a sequence number. A receiver drops packets with an unknown magic or version. Any change to a packet's layout or meaning increments `PROTOCOL_VERSION`, and `static_assert`s on the struct sizes catch accidental layout changes at compile time. Defined: `Hello` (sent at boot) and `Motion` (18 bytes: header plus accel in thousandths of a g and gyro in tenths of a degree per second, as 16-bit integers). The wearables broadcast, so the receiver needs no addresses. All devices use `ESPNOW_CHANNEL` (1) in `protocol.h`; change it everywhere at once to dodge a busy Wi-Fi channel.

## Implemented vs. hardware-unverified

| Item | State |
|---|---|
| Builds for `seeed_xiao_esp32c6` with Arduino | Compiles with no warnings (MINI-PC, 2026-10-28): RAM 4.8%, flash 22.2% |
| Boot, USB serial log, heartbeat | Runs on a board (heartbeat seen in the monitor) |
| Motor pin held LOW from boot | Written; **not checked on hardware** |
| IMU detection and readings | v0.2 run on a board: found at 0x6A, about 1 g at rest, values follow tilting and turning |
| v0.3 `name=value` output at 50 Hz, read by TouchDesigner | Run on a board (LAPTOP, 2026-10-28): `imu_monitor` graphs follow tilting |
| Wearable v0.4 with ESP-NOW | Compiles with no warnings (MINI-PC, 2026-10-28): RAM 13.2%, flash 76.6% (the Wi-Fi stack); **not run on a board** |
| Receiver v0.1 for `nodemcuv2` | Compiles with no warnings (MINI-PC, 2026-10-28): RAM 37.5%, flash 27.1%; **not run on a board** |
| ESP32-C6 to ESP8266 over ESP-NOW | **Untested**; same protocol on both, expected to work |
| Display | **Untested**; controller assumed ST7735, variant `INITR_BLACKTAB` |
| Button, battery | Placeholders only |
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
- **Receiver board:** an ESP8266 for now. Moving to an ESP32 later means a `radio_esp32.cpp` and a new `[env]`; the protocol, the wearable and TouchDesigner stay as they are.
- **Wearable id:** set at build time for now. Flash storage or the MAC address may be easier with many wearables.
