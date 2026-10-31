# Wearable sensor firmware

Firmware for the wireless wearable motion sensors used with the Interactive Dance TouchDesigner toolkit. Each wearable sends its movement over ESP-NOW to a receiver, which passes it on to TouchDesigner.

**Status:**
- **Verified on hardware (LAPTOP, 2026-10-28):** wearable v0.5 and receiver v0.1 with one wearable. The wearable reads the IMU and sends 50 readings a second by ESP-NOW. The receiver (an ESP8266 NodeMCU) forwards them to TouchDesigner over USB and shows status on a small display.
- **Verified on hardware (LAPTOP, 2026-10-29):** wearable v0.7 over USB on a breadboard: the button on D1 (`btn`, and a 1.5 s hold switches wrist/ankle), the vibration motor on D2 through an NPN transistor (2 buzzes for ankle, 1 for wrist, from the button and from `a`/`w`), and the readings lying flat (gyro calibrated, `still=1`, pitch and roll about -1 deg).
- **Verified on hardware (LAPTOP, 2026-10-30):** receiver v0.3 and wearable 1 on v0.8, checks 1-5 and the button and motor below, all six hit directions correct.
- **Not yet run on boards:** wearable v0.9 and receiver v0.4 (battery reading), wearables 2 and 3, and all three together. Hits and the thresholds are untested until the recordings are in.
- **Compiled:** receiver v0.4. Wearable v0.9 compiles file by file with no warnings, but has not been linked yet (see the table below). The wearable works out a small set of dancer signals (activity, tilt, hit with direction, still, button) in wrist or ankle mode, records raw data for tuning, and sends about 100 packets a second. The receiver handles three wearables at once, on the display too.
- **Battery:** the wearable reads the LiPo through a divider and reports a rough percentage. It needs the divider below on every wearable.

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
    config.h            version, id, pins, body axes, send rate, motion and per-mode settings
    protocol.h          versioned ESP-NOW packet layout, shared by wearable and receiver
  src/
    wearable/
      main.cpp          boot, identity, main loop, USB keys, USB log, recording, heartbeat
      imu.*             LSM6DS3TR-C, read directly over I2C (no library)
      motion.*          the dancer signals, worked out on every sample
      mode.*            wrist or ankle, kept in flash
      button.*          debounced button; a long press switches the mode
      haptic.*          vibration motor: off at boot, short buzzes
      espnow_link.*     ESP-NOW broadcast of Hello and Motion packets
      battery.*         battery voltage and rough percentage
    receiver/
      main.cpp          packets in, serial lines out, wearable tracking, duplicate ids, heartbeat
      receiver_config.h version, serial speed, display pins, variant and refresh
      radio.h           ESP-NOW receive queue (the only board-specific interface)
      radio_esp8266.cpp its ESP8266 implementation; an ESP32 receiver adds radio_esp32.cpp
      wearables.h       per-wearable state shared with the display
      display.*         ST7735 status screen
  tools/
    motion_model.py     Python copy of motion.cpp, for tuning on recordings
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

**Updating from v0.5:** flash the receiver first. Receiver v0.2 and later read both old (v0.4-v0.5) and new (v0.7 and later) wearables, but receiver v0.1 ignores v0.7 wearables.

**Versions on the display (receiver v0.3, wearable v0.8):** the receiver shows its own version on the boot screen and in the title bar, and each wearable's version on its row. Wearables from v0.8 repeat their Hello every 2 s, so the version appears even when the receiver is switched on after the wearable; an older wearable shows `v?.?` until it is restarted.

## The dancer signals (wearable v0.7)

Worked out on the wearable from every sensor sample (208 a second), before anything is sent, so short events are caught even between packets. All settings are in `config.h`; **the thresholds are starting values, not yet tuned on a body.**

| Signal | Kind | Meaning |
|---|---|---|
| `act` | 0 to 1 | Activity: how much the wearable is moving. Rises within 0.03 s, falls over about 0.4 s. |
| `gx gy gz` | degrees per second | Rotation speed about the body axes (below), gyro drift removed. `gz` positive = turning left. |
| `pitch` | -90 to 90 degrees | Forward end raised (positive) or lowered: arm or foot lifted. |
| `roll` | -180 to 180 degrees | Rolled right (positive) or left about the forward axis. |
| `hit` | 0 or 1 | 1 for 120 ms when a hit starts: acceleration, with gravity taken away, above the mode's threshold. A punch's counter-spike, within 250 ms, is part of the same hit. |
| `hitdir` | 1 to 6 | Direction of the latest hit's first spike: 1 forward, 2 back, 3 up, 4 down, 5 left, 6 right. 0 before the first hit. |
| `still` | 0 or 1 | 1 after half a second of hardly any movement (a freeze); back to 0 as soon as the wearer moves. |
| `btn` | 0 or 1 | 1 while the button is held. |
| `mode` | 1 or 2 | 1 wrist, 2 ankle. |

`ax ay az` (acceleration in g) are still sent, for `imu_monitor`.

**Body axes.** Wearing standard: chip side facing out, USB connector towards the hand (wrist) or the toes (ankle). Forward is towards the USB, up is out of the chip face, left and right are as seen looking down on the chip face with the USB pointing away. How the IMU board sits on the wearable decides which sensor axis is which; set `BODY_FORWARD_AXIS`, `BODY_LEFT_AXIS` and `BODY_UP_AXIS` in `config.h` (the default assumes the IMU's x points to the USB and its z out of the chip face). **Hand test:** lie it flat, chip up: `pitch` and `roll` near 0. Raise the USB end: `pitch` goes positive. Tip it onto its right edge: `roll` goes positive. Jab it towards the USB: `hitdir` 1 (fwd on the display).

**Modes.** Wrist and ankle use the same signals with their own thresholds (`WRIST_SETTINGS`, `ANKLE_SETTINGS`): ankles take a jolt at every step, so an ankle hit needs about 3 g instead of 1.5 g. Holding the button for 1.5 s switches the mode; the motor buzzes once for wrist, twice for ankle. Typing `w` or `a` in a serial monitor does the same. The mode is kept in flash and shown on the receiver's display, in its serial lines and in TouchDesigner.

**Gyro calibration.** At power-up the wearable averages the gyro over 1 s while it lies still (no axis strays more than 3 deg/s). Until then the bias is 0 and the display shows `cal`. Measured once per power-up.

**Latency:** the wearable checks the sensor every 1 ms and sends every second sample (about every 10 ms) straight away. The receiver prints each packet as soon as it arrives and draws the display in small pieces in between. Worst case from movement to TouchDesigner is about 1 ms (sensor) + 10 ms (send interval) + 2 ms (radio and serial) + one TouchDesigner frame.

Ideas kept for later: `spin` (a sustained turn) and `jump` (brief weightlessness, reliable on the ankle only).

## Recording moves for tuning

The thresholds need real movements. In record mode the wearable prints every raw sample, with what the firmware made of it, so the detectors can be tuned and tested in Python on MINI-PC. Breadboard and hand-held recordings are fine to start.

1. Plug the wearable into LAPTOP. Close TouchDesigner's serial input (only one program can open the port).
2. From the `Firmware` folder: `pio device monitor -b 115200 -f log2file`. The log file is written in that folder.
3. Type `r` to start. Before each move type `m` (a numbered mark), then do the move. Do about 10 of each: punch, stamp, a sharp stop, a freeze, gentle swaying (which must not be a hit).
4. Type `r` to stop, then Ctrl+C. One file per kind of move is easiest; rename it, e.g. `wrist_punch.log`.
5. Put the files in `Firmware/recordings/`, commit and push them.

On MINI-PC, `python tools/motion_model.py recordings/wrist_punch.log` lists each hit with its time, direction and peak, and checks the firmware's results against the Python copy. `--hit 2.0` tries another threshold, `--mode ankle` the other mode.

Record lines start with `#`, so TouchDesigner ignores them; the normal 50-a-second log and the heartbeat pause while recording. ESP-NOW keeps sending.

## Expected serial output (wearable)

```
Interactive Dance wearable v0.7
  wearable id 1, protocol v3, wrist mode
  chip ESP32-C6 rev ..., 160 MHz, efuse MAC ...
  keys: w wrist, a ankle, r record on/off, m mark
[imu] I2C on SDA 22, SCL 23
[imu] I2C devices: 0x6A
[imu] LSM6DS3TR-C ready at 0x6A: 208 Hz, +-8 g, +-2000 dps
[button] pin 1, pull-up; hold 1.5 s to switch wrist/ankle
[battery] 3920 mV, about 64% (ADC pin 0, divider x2.0)
[espnow] broadcasting on channel 1, protocol v3, MAC ...
boot complete
[motion] gyro calibrated, bias 0.41 -0.28 0.12 dps
ax=0.012 ay=-0.021 az=1.003 gx=0.0 gy=0.1 gz=-0.1 pitch=-0.7 roll=-1.2 act=0.004 hit=0 hitdir=0 still=1 btn=0 mode=1
...
[heartbeat] uptime 5 s, wearable 1, fw v0.7, wrist, imu ok at 0x6A, gyro calibrated, hits 0, espnow sent 520 failed 0
```

The boot lines are usually printed before the serial monitor has opened (the board resets after flashing and the USB port reconnects), so often only the later lines show. **Type any other key** to print the identity again. The `[mode]` and `[haptic]` lines print too early to be seen.

The readings are `name=value` lines, 50 a second: TouchDesigner's `inputs` component reads them over USB serial (Read Serial on, 115200) as `serial_ax` ... `serial_mode`. Log lines start with `[` and recordings with `#`, so TouchDesigner ignores them. Close the PlatformIO monitor first: only one program can open the port.

If the IMU says `not found`, the scan line lists what is on the I2C bus: `none` means a wiring or power problem; the firmware keeps looking every 3 s, so a wire can be fixed without a reset.

## Receiver

The receiver listens on ESP-NOW channel 1 and prints one line per Motion packet, at 921600 baud:

```
w1_ax=0.012 w1_ay=-0.021 w1_az=1.003 w1_gx=0.0 w1_gy=0.1 w1_gz=-0.1 w1_pitch=-0.7 w1_roll=-1.2 w1_act=0.004 w1_hit=0 w1_hitdir=0 w1_still=1 w1_btn=0 w1_mode=1
w1_batt=64 w1_battv=3.920
```

Wearables on v0.4-v0.5 send no motion processing, so their lines stop after `w1_gz`. In TouchDesigner (**inputs > Serial**: Read Serial on, the receiver's port, **Baud Rate 921600**) these become `serial_w1_ax` ... `serial_w1_mode`. When a wearable appears or stays silent for a second the receiver prints `w1_live=1`, or `w1_live=0` with `act`, `hit`, `still` and `btn` set to 0, so nothing is left switched on. From wearable v0.9 the battery line arrives every 5 s as `serial_w1_batt` (percent) and `serial_w1_battv` (volts); without a reading they are -1 and 0. Log lines (`[rx] ...`, `[heartbeat] ...` every 5 s with packet rate, losses, hits and battery per wearable) start with `[`.

If two wearables send with the same id (flashed from the same build), the receiver logs both MAC addresses and the display shows `DUP` in yellow on that row. Flash one of them with another id.

Three wearables at about 104 lines a second use about 60% of the 921600 baud line.

The display uses the Project Hub's yellow and black theme (`global-knowledge/design/`). It first shows the wasp logo and the receiver version for 2 s, inside a yellow and black hazard frame. This is also the wiring check: the logo must be yellow (cyan means red and blue are swapped) and the frame must show on all four edges; otherwise change `RX_TFT_TAB` in `receiver_config.h`. Then it shows three rows, for wearables 1, 2 and 3, always, even before they appear (`waiting`):

```
W1 v0.8 wrist LIVE 104 x0       firmware version, mode, LIVE / LOST / DUP, packets a second, lost in the last second
[accel x][accel y][accel z]     bars: x orange-red, y yellow, z cream
[gyro x ][gyro y ][gyro z ]
[activity] fwd S B p-12  100%   activity (amber during a hit), hit direction (or cal), S still, B button, pitch, battery
```

Row colours: yellow LIVE, orange-red LOST, amber DUP. An old wearable shows `old fw: no tilt`. The yellow title bar shows the receiver version (`RX v0.3`), the channel, `+N` when wearables with ids above 3 are live (they still reach TouchDesigner), and the uptime. The display is redrawn every 100 ms, one piece per loop pass (the title or one row, a few milliseconds each), so serial output is never held back for long.

## Protocol

`include/protocol.h` defines the packets. Every packet starts with a 6-byte header: magic `0xDA`, protocol version, packet type, wearable id and a sequence number. A receiver drops packets with an unknown magic or a version outside the range it reads (v2 to v3). Any change to a packet's layout or meaning increments `PROTOCOL_VERSION`, and `static_assert`s on the struct sizes catch accidental layout changes at compile time.

- `Hello`: sent at boot with the firmware version, and every 2 s from wearable v0.8.
- `Motion` v3: 28 bytes, all on the body axes. Header; accel in thousandths of a g; gyro (drift removed) in tenths of a degree per second; pitch and roll in tenths of a degree; activity 0 to 1000; flags (hit, still, button, gyro calibrated); hit direction; hit counter; mode.
- `Battery`: 9 bytes, every 5 s from wearable v0.9. Header; smoothed millivolts (0 = no reading); percent. It is a new packet type inside protocol v3, so older boards keep working: receiver v0.3 only counts it as a bad packet.
- `Motion` v2: 18 bytes, the raw values only (wearable v0.4-v0.5).

The wearables broadcast, so the receiver needs no addresses. All devices use `ESPNOW_CHANNEL` (1) in `protocol.h`; change it everywhere at once to dodge a busy Wi-Fi channel.

## Implemented vs. hardware-unverified

| Item | State |
|---|---|
| Boot, USB serial log, heartbeat | Runs on a board |
| IMU detection and readings | Run on a board: found at 0x6A, about 1 g at rest, values follow tilting and turning |
| Wearable v0.5, ESP-NOW at 50 Hz | Run on boards (LAPTOP, 2026-10-28), one wearable |
| Receiver v0.1 on `nodemcuv2`, display | Run on boards (LAPTOP, 2026-10-28): display, LIVE status, bars, TouchDesigner at 921600 |
| ESP32-C6 to ESP8266 over ESP-NOW | Works (LAPTOP, 2026-10-28) |
| Wearable v0.7: 208 Hz, +-8 g, dancer signals, modes, recording, about 104 packets a second | Compiles with no warnings (MINI-PC, 2026-10-29): RAM 13.2%, flash 77.7%; **not run on a board** |
| Wearable v0.8: Hello repeated every 2 s | Flashed on wearable 1 and checked on LAPTOP (2026-10-30). PlatformIO Core 6.2.0.post1 on MINI-PC refuses the pinned pioarduino platform, so the wearable does not build there |
| `wearable2`, `wearable3` builds (ids 2 and 3) | Compile; **not run on boards** |
| Receiver v0.2: protocol v2 and v3, three-row display, duplicate ids, piecewise drawing | Compiles with no warnings (MINI-PC, 2026-10-29): RAM 38.4%, flash 27.4%; **not run on a board** |
| Receiver v0.3: yellow and black theme, logo on boot, versions on the display | Flashed and checked on LAPTOP (2026-10-30). Compiles with no warnings: RAM 38.5%, flash 27.4% |
| Detector design (one hit per punch, direction, still, tilt, modes) | `tools/motion_model.py`, tested on made-up movements (`tests/test_motion_model.py`); the C++ itself has no automated test |
| Thresholds | Starting values, **not tuned**: needs recordings, then a body |
| Button, motor | Code written; parts **not wired yet** |
| Wearable v0.9: battery reading, Battery packet | Each changed file compiles with no warnings using the C6 toolchain directly (MINI-PC, 2026-10-30), but it is **not linked or run**: PlatformIO on MINI-PC refuses the platform, so build it on LAPTOP |
| Receiver v0.4: battery on the display and to TouchDesigner | Compiles with no warnings (MINI-PC, 2026-10-30): RAM 38.6%, flash 27.5%; **not run on a board** |
| Body axes in `config.h` | Assumed; **check with the hand test** |

To check on the hardware:

1. **Receiver v0.3 with the old wearable:** flash the receiver only. The v0.5 wearable must still show LIVE about 50/s, with `old fw: no tilt`, and TouchDesigner must still move with your mappings.
2. **Wearable v0.8:** flash wearable 1 and leave it still for a second after power-up. The monitor (115200) shows `[motion] gyro calibrated`, the display row shows `v0.8` and `wrist`, `cal` clears, and the rate is about 104 with `x0`.
3. **Body axes:** the hand test above. If a direction is wrong, change the `BODY_*_AXIS` lines and reflash.
4. **Signals:** shake it: activity rises and falls back within about half a second. Jab it: `fwd` shows and `serial_w1_hit` goes to 1. Put it down: `S` after half a second.
5. **Mode:** type `a` in the monitor: the row shows `ankle`, and a jab that was a hit in wrist mode needs to be harder.
6. **Three wearables:** flash `wearable2` and `wearable3` onto the others. All three rows LIVE at about 104/s, no `DUP`.
7. **TouchDesigner load:** with all three running, check the frame rate stays where it was. If it drops, set `ESPNOW_SEND_EVERY_SAMPLES` to 4.
8. **Recordings** for tuning (above).
9. Once wired: the button (hold 1.5 s to switch mode, `B` while held) and the motor (one or two buzzes; never on at power-up).
10. **Battery:** see below.

### Battery

Every wearable needs a divider, because the XIAO has none built in and 4.2 V straight into A0 would exceed its 3.3 V limit. Two equal 100k resistors from BAT+ to GND, with the middle point on A0 (optionally 100 nF from A0 to GND). Never connect BAT+ straight to A0.

1. Flash receiver v0.4 and wearable v0.9; boards can be flashed in any order.
2. Run on the battery with USB unplugged, and measure the battery with a multimeter. On USB the reading follows the charger, not the cell.
3. Compare with `battery ... mV` in the heartbeat or `serial_w1_battv`. If they differ by more than about 50 mV, change `BATTERY_DIVIDER_RATIO` to (ratio x measured / shown).

The display shows the percentage at the end of the wearable's lower line: cream, amber at 20% or below, orange-red at 10% or below, `--` without a reading. It settles a few seconds after power-up. The percentage is rough (a typical LiPo curve): it dips while the motor runs and differs from cell to cell, so use it as a guide and take the real run time from the battery life test. An unwired A0 floats and can show a made-up value now and then.

## Decisions to revisit

- **Pins:** I2C on D4/D5 (the board's default I2C pins), button D1, motor D2, battery A0. The XIAO ESP32-C6 has no on-board battery voltage divider, so the battery needs an external one into A0.
- **Antenna:** the board support code (`initVariant`) turns on the RF switch (GPIO3 LOW) and selects the on-board antenna (GPIO14 LOW) at boot, so the firmware leaves those pins alone. For an external antenna, set GPIO14 HIGH after boot. Check ESP-NOW range on the real costume.
- **Receiver board:** an ESP8266 for now. Moving to an ESP32 later means a `radio_esp32.cpp` and a new `[env]`; the protocol, the wearable and TouchDesigner stay as they are.
- **Wearable id:** set at build time (one build environment per id). Flash storage or the MAC address may be easier with many wearables.
- **Signals worked out on the wearable**, not in TouchDesigner: the wearable sees every sample at 208 Hz, while TouchDesigner sees about 100 packets a second and reads once per frame. Changing a threshold means reflashing; once tuned that should be rare.
- **Hit direction** is taken from the first spike above the threshold. For a stamp the first big spike may be the impact (pointing up), not the downward movement; the recordings will show which, and the rule can differ per mode.
- **Send rate:** about 104 packets a second per wearable for low latency. If TouchDesigner's frame rate suffers with three wearables, set `ESPNOW_SEND_EVERY_SAMPLES` to 4 (52 a second).
