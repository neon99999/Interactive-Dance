# Development status

Last updated 2026-10-27.

**Latest working project:** `TouchDesigner/DanceWorkshop.toe`, at git commit `f8df998` or later on `main`. It was saved, reopened and retested: all 63 checks pass. All commits are pushed to GitHub.

## Milestones

| # | Milestone | Commit | State |
|---|---|---|---|
| T01 | Synced audio + MIDI transport | `e6fa517` | Done, tested |
| 1 | MIDI assignment table and engine | `150aebd` | Done, tested |
| 2 | First visual layer driven by MIDI | `5ee057d` | Done, tested (rendered pixels) |
| 3 | Seeking and state reconstruction | `db91e91` | Done, tested, including during real playback |
| 4 | Four layers and compositor | `c196a3e` | Done, tested (rendered pixels) |
| 5 | Content types, effects, flash/fade/blackout, text | `c70f969` | Done, tested (rendered pixels; a still image, not a movie) |
| 6 | Simulated movement input | `ed5ae8a` | Done, tested |
| 7 | OSC, serial and camera adapters | `50d1363` | OSC tested locally. Serial: parser only, no hardware. Camera: test pattern only, no webcam |
| 8 | Usability and documentation | `f8df998` | Done. Output-window buttons tested; table buttons tested with a stub (no windows opened) |
| 9 | MIDI note monitor (`midi_monitor`) | see git log | Done. Tested with the user's own MIDI file: seek, and notes appearing and clearing during playback |

## Tests

**In TouchDesigner:** run `op('/project1/tests/engine_tests').module.Run()`. Results go to `tests/results`; the last run, after a reopen, passed **63 of 63**.

- **engine (12):** each action; a chord with simultaneous events; a conflict where the later row wins; pause; forward and backward seek; seek into a trigger window; reset; repeated playback.
- **playback (2):** during real playback, the live values equal a fresh evaluation at the clock time (30 samples); the clock advances.
- **config (3):** 4 invalid rows are reported, the engine keeps running, and the valid row still applies.
- **render (26):** output pixels for show, colour, position, fade, flash, hide, level, blackout, every content type and effect, four-layer order and opacity.
- **inputs (20):**
  - range mapping, inverted range, smoothing, trigger, zone, and a missing signal
  - the music stays paused while inputs act
  - invalid rows
  - OSC over local UDP
  - serial lines: name=value pairs, plain numbers with names, and a bad line
  - the camera test pattern, camera off, and camera selected with no camera attached
  - all inputs off restores the base values

**Plain Python:** `python -m unittest discover -s tests`: **35 of 35** pass (27 show logic, 9 serial parser). 2000 notes evaluate in under 1 ms.

**Save/reopen:** TouchDesigner was relaunched on the saved project; there were no errors, pages, tables and annotations were intact, and all 63 checks passed.

**Task 01 sync test:** `op('/project1/test_t01/sync_test').module.Start()` (passed when Task 01 was done).

## Verified by hand (2026-10-27)

- **Listening:** the user played the test track and the visuals line up with the audio. The output buffer still adds a small delay (about 0.15 s, more over remote desktop); there is no latency setting yet.
- **Simulated inputs:** the user drove the simulated channels and saw the visuals respond.

## Verified on hardware (2026-10-28, LAPTOP)

- **Wearable IMU over USB serial:** a XIAO ESP32-C6 with the LSM6DS3TR-C (firmware v0.3, branch `feature/wearable-sensors`) sent readings to `inputs > Serial` on COM4, and the `imu_monitor` graphs moved when the user tilted it. This is the first real serial device. The user then mapped the IMU signals in the input assignment table and they drove a visual.
- **Wireless (ESP-NOW):** the wearable (fw v0.4) broadcast its IMU readings to a NodeMCU 1.0 (ESP8266) receiver, whose ST7735 display showed the wearable LIVE with moving bars. Through the receiver on COM3 at 921600 baud, TouchDesigner received `serial_w1_ax` ... and an input assignment drove a visual.
- **Found on hardware:** the TouchDesigner Serial DAT's default DTR setting held the NodeMCU in reset (its USB chip drives the reset pins), so `serial_in` now has DTR and RTS off. The wearable stalled its radio while its USB cable was plugged in with no program reading it; fixed in fw v0.5 (not yet flashed). imu_monitor with the receiver's `serial_w1_` prefix was checked here with simulated lines only.

## Not verified (needs a person or hardware)

- **Movies:** Content "media" was tested with a still image. A movie plays on its own clock, not synced to the music, seek or pause.
- **Real webcam:** none on this machine, which runs over remote desktop. The camera chain was tested with the moving test pattern.
- **OSC from another device:** only tested from this computer to itself (127.0.0.1). Another device may also need the Windows firewall to allow TouchDesigner, and the user decides that.
- **macOS:** untested. Nothing Windows-specific was used. The camera driver and serial port names differ, and both are picked from menus.
- **Frame rate:** 40-55 fps on this machine. The project's own cook time is near zero, so the limit is the machine and setup (a second TouchDesigner instance, remote desktop). Check on the show computer.
- **Engine table buttons:** they call `openViewer()`. The routing was tested, but the windows were not opened during tests.
- **Output window on a projector:** it opens and closes; the monitor choice was not tested.

## Known limitations

- Only Note On is used (no velocity, channel or Note Off).
- If a sensor stops sending, its last OSC or serial value holds until the source is turned off.
- OSC address names keep their slashes (`dancer/level`), which can look odd in tables.
- The camera signals are raw motion amounts, so they need **Sensitivity** or an input range to tune.
- `layer2`-`layer4` are clones: edit the network inside `layer1` only.
- Notes are reported up to one frame late (17 ms at 60 fps).
- The engine replays every note up to the playback position each frame, so its cost grows with the song's note count: 0.14 ms per frame for a few notes, about 4 ms at the end of a 5,000-note file (measured 2026-10-28). Songs are expected to have at most about 100 notes, so this is not optimized. If dense files are ever needed, keep state snapshots every few seconds and replay from the nearest one.

## Deferred

- An audio latency offset, until it is measured on the show setup.
- Movie playback synced to the music.
- MediaPipe body tracking: documented in the README, not included; it needs a download.
- A timeout that drops stale sensor values.
- A friendlier editor than the table viewers.

## Dependencies

- TouchDesigner 2025.32280 or later. The project uses only native operators and no extra Python packages.
- Embody/Envoy, which ships in the project, saves components as text. It is not needed to run the toolkit.
- The unit tests need Python 3.10 or later, standard library only.

## Manual tests to do

1. ~~Play the test track and listen~~ (done 2026-10-27).
2. Put a movie in `layer1` (Content media, Media File) and check playback and performance.
3. Send OSC from a phone or another computer to port 7000, e.g. `/dancer/level 0.5`, with **Receive OSC** on.
4. ~~Connect a serial device~~ (wearable IMU, done 2026-10-28, including driving a visual through the input table).
5. Plug in a webcam, set Camera **Source** to Camera, wave left and right, and watch `camera_left` / `camera_right`.
6. Open the project on a Mac and run the tests.
7. Press the Assignments buttons on `engine` and the Output buttons on `visuals`.
