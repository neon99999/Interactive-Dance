# Wearable sensor firmware

Firmware for the wireless wearable motion sensors used with the Interactive Dance TouchDesigner toolkit. Each wearable sends its movement over ESP-NOW to a receiver, which passes it on to TouchDesigner.

**Status:**
- **Verified on hardware (LAPTOP, 2026-10-28):** wearable v0.5 and receiver v0.1 with one wearable. The wearable reads the IMU and sends 50 readings a second by ESP-NOW. The receiver (an ESP8266 NodeMCU) forwards them to TouchDesigner over USB and shows status on a small display.
- **Compiled, not yet run on boards:** wearable v0.6 and receiver v0.2. The wearable adds motion processing (tilt, activity, hits) and sends about 100 packets a second. The receiver handles three wearables at once, on the display too.
- The button, motor and battery modules are still placeholders.

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
  platformio.ini        build environments: wearable (id 1), wearable2, wearable3, receiver
  include/
    config.h            firmware version, wearable id, pins, IMU, send rate, motion settings
    protocol.h          versioned ESP-NOW packet layout, shared by wearable and receiver
  src/
    wearable/
      main.cpp          boot, identity log, module start-up, main loop, USB log, heartbeat
      imu.*             LSM6DS3TR-C, read directly over I2C (no library)
      motion.*          gyro calibration, tilt, activity and hit detection on every sample
      espnow_link.*     ESP-NOW broadcast of Hello and Motion packets
      button.*          pushbutton (placeholder)
      haptic.*          vibration motor (holds the motor pin LOW; no patterns yet)
      battery.*         battery voltage (placeholder)
    receiver/
      main.cpp          packets in, serial lines out, wearable tracking, duplicate ids, heartbeat
      receiver_config.h version, serial speed, display pins, variant and refresh
      radio.h           ESP-NOW receive queue (the only board-specific interface)
      radio_esp8266.cpp its ESP8266 implementation; an ESP32 receiver adds radio_esp32.cpp
      wearables.h       per-wearable state shared with the display
      display.*         ST7735 status screen
```

Each module has `begin()` and `update()`; `main.cpp` calls them, so a module is filled in without touching the others. `build_src_filter` keeps the wearable and receiver sources apart in one project.

## Building

Needs [PlatformIO Core](https://platformio.org/install/cli) (or the VS Code PlatformIO extension). From this folder:

```
pio run -e wearable -t upload          # flash wearable 1 over USB
pio run -e wearable2 -t upload         # ... wearable 2
pio run -e wearable3 -t upload         # ... wearable 3
pio device monitor -b 115200           # wearable serial log
pio run -e receiver -t upload          # flash the receiver (NodeMCU)
pio device monitor -b 921600           # receiver log
```

**Every wearable needs its own id.** `wearable`, `wearable2` and `wearable3` build the same firmware with ids 1, 2 and 3; two wearables with the same id show as `DUP` on the receiver. For more wearables, copy the `[env:wearable3]` block with the next id (the receiver accepts ids 1 to 8, the display shows 1 to 3).

The first build downloads the platform and toolchain (about 1 GB). On Windows, run it from PowerShell, cmd or VS Code, **not Git Bash**: the ESP-IDF tool installer refuses MSYS shells, which leaves the compiler uninstalled (`'riscv32-esp-elf-g++' is not recognized`) or the build without `esptool`.

**Platform:** the official `espressif32` platform supports the XIAO ESP32-C6 only with ESP-IDF. For the Arduino framework this project uses the community [pioarduino](https://github.com/pioarduino/platform-espressif32) platform, pinned to release `55.03.312-1` (Arduino core 3.3.12, ESP-IDF 5.5.5). Change the version deliberately and on every machine at once.

**Updating from v0.5:** flash the receiver first. Receiver v0.2 reads both old (v0.4-v0.5) and new (v0.6) wearables, but receiver v0.1 ignores v0.6 wearables.

## Expected serial output (wearable)

```
Interactive Dance wearable v0.6
  wearable id 1, protocol v3
  chip ESP32-C6 rev ..., 160 MHz, efuse MAC ...
[imu] I2C on SDA 22, SCL 23
[imu] I2C devices: 0x6A
[imu] LSM6DS3TR-C ready at 0x6A: 208 Hz, +-8 g, +-2000 dps
[button] placeholder: pin 1, not read
[battery] placeholder: ADC pin 0, divider x2.0, not read
[espnow] broadcasting on channel 1, protocol v3, MAC ...
boot complete
[motion] gyro calibrated, bias 0.41 -0.28 0.12 dps
ax=0.012 ay=-0.021 az=1.003 gx=0.0 gy=0.1 gz=-0.1 pitch=-0.7 roll=-1.2 act=0.004 hit=0
...
[heartbeat] uptime 5 s, wearable 1, fw v0.6, imu ok at 0x6A, gyro calibrated, hits 0, espnow sent 520 failed 0
```

The boot lines are usually printed before the serial monitor has opened (the board resets after flashing and the USB port reconnects), so often only the later lines show. **Type any key in the monitor** to print the identity again; the heartbeat line also shows the firmware version and the IMU state. The `[haptic]` line always prints too early to be seen.

Readings are `name=value` lines, 50 a second on USB: `ax ay az` in g, `gx gy gz` in degrees per second, then the motion processing below. TouchDesigner's `inputs` component reads them over USB serial (Read Serial on, 115200) as `serial_ax` ... `serial_hit`, and `imu_monitor` graphs the raw values. Log lines start with `[` so TouchDesigner ignores them. Close the PlatformIO monitor first: only one program can open the port.

Lying flat and still, the IMU should read about 1 g on one axis and close to 0 on the others, with the gyro near 0. If it says `not found`, the scan line lists what is on the I2C bus: `none` means a wiring or power problem; the firmware keeps looking every 3 s, so a wire can be fixed without a reset.

## Motion processing (wearable v0.6)

`motion.cpp` runs on every sensor sample (208 a second), before anything is sent, so short events such as a stamp are caught even between packets. All settings are in `config.h`.

| Value | How |
|---|---|
| Gyro bias | Averaged over 1 s while the wearable is still (no axis strays more than 3 deg/s), then subtracted from `gx gy gz`. Until then the bias is 0, the wearable logs `hold the wearable still`, and the receiver shows `cal`. Measured once per power-up. |
| `pitch`, `roll` | Tilt from gravity in degrees, by a complementary filter: the gyro follows fast turns, gravity corrects drift with a 0.5 s time constant, and gravity is ignored while the acceleration is more than 0.25 g away from 1 g (jumps, hits). Sensor axes: roll about x, pitch about y, both 0 lying flat. Roll is unreliable near pitch +-90. |
| `act` | 0 to 1: the larger of (acceleration away from 1 g) / 1.5 g and (rotation speed) / 600 deg/s, rising within 0.03 s and falling within 0.4 s. |
| `hit` | 1 for 120 ms after the acceleration goes more than 1.5 g above gravity; held that long so TouchDesigner, which reads once per frame, cannot miss it. The next hit needs the acceleration to fall below 0.75 g above gravity and 150 ms to pass. The packet also counts hits (shown in the receiver's heartbeat). |

The accelerometer range is +-8 g (it was +-4 g, which clipped hard stamps); `ax ay az` are still in g.

**Latency:** the wearable checks the sensor every 1 ms and sends every second sample (about every 10 ms) straight away. The receiver prints each packet as soon as it arrives and draws the display in small pieces in between. Worst case from movement to TouchDesigner is about 1 ms (sensor) + 10 ms (send interval) + 2 ms (radio and serial) + one TouchDesigner frame.

## Receiver

The receiver listens on ESP-NOW channel 1 and prints one line per Motion packet, at 921600 baud:

```
w1_ax=0.012 w1_ay=-0.021 w1_az=1.003 w1_gx=0.0 w1_gy=0.1 w1_gz=-0.1 w1_pitch=-0.7 w1_roll=-1.2 w1_act=0.004 w1_hit=0
```

Wearables on v0.4-v0.5 send no motion processing, so their lines stop after `w1_gz`. In TouchDesigner (**inputs > Serial**: Read Serial on, the receiver's port, **Baud Rate 921600**) these become `serial_w1_ax` ... `serial_w1_hit`; to graph wearable 2, set imu_monitor's **Signal Prefix** to Wearable 2 (`serial_w2_`). When a wearable appears or stays silent for a second the receiver prints `w1_live=1`, or `w1_live=0 w1_act=0 w1_hit=0`. Log lines (`[rx] ...`, `[heartbeat] ...` every 5 s with packet rate, losses and hits per wearable) start with `[`.

If two wearables send with the same id (flashed from the same build), the receiver logs both MAC addresses and the display shows `DUP` in yellow on that row. Flash one of them with another id.

Three wearables at about 104 lines a second use about 45% of the 921600 baud line.

The display first shows a colour test card for 1.5 s: red, green, blue and white stripes left to right, with a yellow frame on all four edges. If red and blue are swapped or an edge shows noise, change `RX_TFT_TAB` in `receiver_config.h`. Then it shows three rows, for wearables 1, 2 and 3, always, even before they appear (`waiting`):
- `W1 LIVE 104/s lost 0`: LIVE, LOST or DUP, packets per second, lost packets
- bars for acceleration (top) and rotation (middle), x red, y green, z blue
- an activity bar (yellow during a hit), then `HIT` or `cal`, and the tilt `p` (pitch) and `r` (roll) in degrees. An old wearable shows `old fw: no tilt`.

The title shows the channel, `+N` when wearables with ids above 3 are live (they still reach TouchDesigner), and the uptime. The display is redrawn every 100 ms, one piece per loop pass (the title or one row, a few milliseconds each), so serial output is never held back for long.

## Protocol

`include/protocol.h` defines the packets. Every packet starts with a 6-byte header: magic `0xDA`, protocol version, packet type, wearable id and a sequence number. A receiver drops packets with an unknown magic or a version outside the range it reads (now v2 to v3). Any change to a packet's layout or meaning increments `PROTOCOL_VERSION`, and `static_assert`s on the struct sizes catch accidental layout changes at compile time.

- `Hello`: sent at boot, with the firmware version.
- `Motion` v3: 26 bytes. Header, accel in thousandths of a g, gyro (bias removed) in tenths of a degree per second, pitch and roll in tenths of a degree, all 16-bit integers; activity 0 to 1000; a flags byte (hit, gyro calibrated); a hit counter.
- `Motion` v2: 18 bytes, the raw values only (wearable v0.4-v0.5).

The wearables broadcast, so the receiver needs no addresses. All devices use `ESPNOW_CHANNEL` (1) in `protocol.h`; change it everywhere at once to dodge a busy Wi-Fi channel.

## Implemented vs. hardware-unverified

| Item | State |
|---|---|
| Boot, USB serial log, heartbeat | Runs on a board |
| Motor pin held LOW from boot | Written; **not checked on hardware** |
| IMU detection and readings | Run on a board: found at 0x6A, about 1 g at rest, values follow tilting and turning |
| Wearable v0.5, ESP-NOW at 50 Hz | Run on boards (LAPTOP, 2026-10-28), one wearable |
| Receiver v0.1 on `nodemcuv2`, display | Run on boards (LAPTOP, 2026-10-28): display, LIVE status, bars, TouchDesigner at 921600 |
| ESP32-C6 to ESP8266 over ESP-NOW | Works (LAPTOP, 2026-10-28) |
| Wearable v0.6: 208 Hz, +-8 g, motion processing, about 104 packets a second | Compiles with no warnings (MINI-PC, 2026-10-29): RAM 13.2%, flash 77.0%; **not run on a board** |
| `wearable2`, `wearable3` builds (ids 2 and 3) | Compile; **not run on boards** |
| Receiver v0.2: protocol v2 and v3, three-row display, duplicate ids, piecewise drawing | Compiles with no warnings (MINI-PC, 2026-10-29): RAM 38.2%, flash 27.4%; **not run on a board** |
| Motion processing thresholds (hit 1.5 g, activity scales, tilt filter) | Starting values, **not tuned on a dancer** |
| Button, battery | Placeholders only |
| Pin numbers in `config.h` | IMU on D4/D5 matches the wiring; button, motor, battery **provisional** |

The motion processing has no automated test: there is no C++ compiler for this computer installed, only the ones for the boards.

To check on the hardware:

1. **Receiver v0.2 with the old wearable:** flash the receiver only. The v0.5 wearable must still show LIVE about 50/s, with `old fw: no tilt`, and TouchDesigner must still move with your mappings.
2. **Wearable v0.6:** flash wearable 1 and leave it still for a second after power-up. The monitor (115200) shows `[motion] gyro calibrated`, the receiver row changes from `cal` to blank, and the rate is about 104/s with `lost` near 0.
3. **Tilt:** tip the sensor forwards and sideways: `p` and `r` follow, return near 0 lying flat, and do not drift over a minute of stillness.
4. **Activity and hit:** shake it: the activity bar rises and falls back within about half a second. Stamp or tap it sharply: `HIT` shows and `serial_w1_hit` goes to 1 in TouchDesigner. Note any missed or false hits while walking.
5. **Three wearables:** flash `wearable2` and `wearable3` onto the others. All three rows LIVE at about 104/s each, `lost` growing slowly at most, and no `DUP`. Flash two with the same id once to see `DUP`.
6. **Latency and load in TouchDesigner:** with all three running, check the frame rate stays where it was, and that a hit-to-flash mapping feels immediate. If the frame rate drops, set `ESPNOW_SEND_EVERY_SAMPLES` to 4.
7. **Lost wearable:** switch one off: within a second its row says LOST and `serial_wN_act` and `serial_wN_hit` drop to 0.
8. Confirm the motor does not run at power-up or reset.
9. Check every pin in `config.h` against the actual wiring.
10. Measure the battery divider and set `BATTERY_DIVIDER_RATIO`.

## Decisions to revisit

- **Pins:** I2C on D4/D5 (the board's default I2C pins), button D1, motor D2, battery A0. The XIAO ESP32-C6 has no on-board battery voltage divider, so the battery needs an external one into A0.
- **Antenna:** the board support code (`initVariant`) turns on the RF switch (GPIO3 LOW) and selects the on-board antenna (GPIO14 LOW) at boot, so the firmware leaves those pins alone. For an external antenna, set GPIO14 HIGH after boot. Check ESP-NOW range on the real costume.
- **Receiver board:** an ESP8266 for now. Moving to an ESP32 later means a `radio_esp32.cpp` and a new `[env]`; the protocol, the wearable and TouchDesigner stay as they are.
- **Wearable id:** set at build time (one build environment per id). Flash storage or the MAC address may be easier with many wearables.
- **Motion processing on the wearable**, not in TouchDesigner: the wearable sees every sample at 208 Hz, while TouchDesigner sees about 100 packets a second and reads once per frame. Changing a threshold means reflashing; if they need tuning live at the workshop, they could move to TouchDesigner parameters later.
- **Send rate:** about 104 packets a second per wearable for low latency. If TouchDesigner's frame rate suffers with three wearables, set `ESPNOW_SEND_EVERY_SAMPLES` to 4 (52 a second).
