# Development status

Last updated 2026-10-29. The wearable work is on branch `feature/wearable-sensors`, not yet merged into `main`.

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

**Plain Python:** `python -m unittest discover -s tests`: **50 of 50** pass (27 show logic, 10 serial parser including the receiver's v0.2 line format, 13 motion model). 2000 notes evaluate in under 1 ms.

**Save/reopen:** TouchDesigner was relaunched on the saved project; there were no errors, pages, tables and annotations were intact, and all 63 checks passed.

**Task 01 sync test:** `op('/project1/test_t01/sync_test').module.Start()` (passed when Task 01 was done).

## Verified by hand (2026-10-27)

- **Listening:** the user played the test track and the visuals line up with the audio. The output buffer still adds a small delay (about 0.15 s, more over remote desktop); there is no latency setting yet.
- **Simulated inputs:** the user drove the simulated channels and saw the visuals respond.

## Verified on hardware (2026-10-28, LAPTOP)

- **Wearable IMU over USB serial:** a XIAO ESP32-C6 with the LSM6DS3TR-C (firmware v0.3, branch `feature/wearable-sensors`) sent readings to `inputs > Serial` on COM4, and the `imu_monitor` graphs moved when the user tilted it. This is the first real serial device. The user then mapped the IMU signals in the input assignment table and they drove a visual.
- **Wireless (ESP-NOW):** the wearable (fw v0.4) broadcast its IMU readings to a NodeMCU 1.0 (ESP8266) receiver, whose ST7735 display showed the wearable LIVE with moving bars. Through the receiver on COM3 at 921600 baud, TouchDesigner received `serial_w1_ax` ... and an input assignment drove a visual.
- **Found on hardware:** the TouchDesigner Serial DAT's default DTR setting held the NodeMCU in reset (its USB chip drives the reset pins), so `serial_in` now has DTR and RTS off. The wearable stalled its radio while its USB cable was plugged in with no program reading it; fixed in fw v0.5.
- **Wireless with fw v0.5:** the user flashed v0.5 and confirmed the whole chain: wearable to receiver over ESP-NOW, the receiver display, TouchDesigner at 921600 baud, input assignments (`serial_w1_ax` to `layer1.x`, `serial_w1_ay` to `layer1.y`) driving the visuals, and `imu_monitor` with prefix `serial_w1_`.
- **Still to check on LAPTOP:** commit `7184ee0` restored the imu_monitor prefix menu, the no-data hint, the baud help and DTR off, which a save from a TouchDesigner session left open across a `git pull` had reverted. The files were checked by hand but not yet loaded in TouchDesigner, and the 63 in-TD tests have not been run on this branch. Close TouchDesigner before every `git pull`.

## Built, not yet on hardware (2026-10-29, branch `feature/wearable-sensors`)

Details in `Firmware/README.md`. All four firmware builds (`wearable`, `wearable2`, `wearable3`, `receiver`) compile with no warnings in our code.

- **Agreed signal set** (with the user, 2026-10-29), per wearable: `act` (0-1), rotation `gx gy gz`, tilt `pitch` and `roll`, `hit` with `hitdir` (1-6 on the body: forward, back, up, down, left, right), `still` (a freeze) and `btn`, plus `mode`. Raw acceleration stays for `imu_monitor`. Kept for later: `spin` and `jump`.
- **Wearable fw v0.7:** the signals are worked out on every sensor sample (now 208 Hz, +-8 g), on body axes (chip side out, USB towards the hand or toes; the IMU's axes are mapped in `config.h`). A punch and its counter-spike count as one hit; the direction is the first spike's. Wrist and ankle modes with their own thresholds (starting values); a 1.5 s button press or `w`/`a` over USB switches, kept in flash, confirmed by 1 or 2 motor buzzes. Record mode (`r` over USB) prints every raw sample for tuning. About 104 packets a second. Build environments for ids 1, 2 and 3.
- **Protocol v3:** the Motion packet carries the signals. The receiver still reads v2 packets, so a v0.5 wearable keeps working with the new receiver (flash the receiver first).
- **Receiver fw v0.2:** prints the signals after the raw values; zeroes `act`, `hit`, `still` and `btn` when a wearable is lost; detects two wearables with the same id (`DUP`). The display always shows rows for wearables 1-3 with the mode, an activity bar, hit direction, still and button markers and tilt, and draws one small piece per loop pass so serial output to TouchDesigner goes first.
- **Tuning tool:** `Firmware/tools/motion_model.py`, a Python copy of the detectors that reads the numbers from `config.h`, analyses recordings and checks them against the firmware's own results. `tests/test_motion_model.py` (13 tests) checks the design on made-up movements: one hit per punch with its counter-spike, two punches, all six directions, the axis mapping, ankle vs wrist thresholds, tilt, activity, still.
- **Not tested automatically:** the C++ itself (no C++ compiler for this computer on MINI-PC).
- **TouchDesigner panel `wearable_monitor`** (2026-10-29, MINI-PC): one card per wearable with the mode, LIVE / NO SIGNAL, bars for activity, gyro x/y/z, pitch and roll, and lamps for hit (with direction), still and button. **Show Wearable** shows all three side by side or one full width. Tested in TouchDesigner by feeding made-up receiver lines through the real serial callback (`serial_in_callbacks.onReceive`): the values, bars, lamps, mode and the one-wearable view were checked by captured frames, LIVE turns on while readings change, goes off 1 s after they stop and at once on `wN_live=0`. Not yet seen with a real wearable. Its cook cost is about 3-4 ms per frame while it is on screen (two Text TOPs and their tables re-cook every frame); nothing while it is not shown.
- **MINI-PC TouchDesigner brought back in line with the files:** after a restart the live `imu_monitor` and `inputs` still had the old prefix field and DTR on; they were reloaded from their `.tdxn` files (DTR off and the prefix menu are now live). The in-TD tests passed 63 of 63 afterwards (one earlier run had 2 engine timing checks fail at about 40 fps; the rerun passed).

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
- If a sensor stops sending, its last OSC or serial value holds until the source is turned off. Exception: through the receiver (fw v0.2), a lost wearable's `act` and `hit` drop to 0.
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
- More wearable signals: `spin` (a sustained turn) and `jump` (brief weightlessness, reliable on the ankle only).

## Dependencies

- TouchDesigner 2025.32280 or later. The project uses only native operators and no extra Python packages.
- Embody/Envoy, which ships in the project, saves components as text. It is not needed to run the toolkit.
- The unit tests need Python 3.10 or later, standard library only.

## Manual tests to do

1. ~~Play the test track and listen~~ (done 2026-10-27).
2. Put a movie in `layer1` (Content media, Media File) and check playback and performance.
3. Send OSC from a phone or another computer to port 7000, e.g. `/dancer/level 0.5`, with **Receive OSC** on.
4. ~~Connect a serial device~~ (wearable IMU, done 2026-10-28, over USB and wirelessly through the receiver, including driving a visual through the input table).
5. Plug in a webcam, set Camera **Source** to Camera, wave left and right, and watch `camera_left` / `camera_right`.
6. Open the project on a Mac and run the tests.
7. Press the Assignments buttons on `engine` and the Output buttons on `visuals`.
8. On the wearable, confirm the pins and test the button, vibration motor and battery reading (still placeholders in the firmware).
9. Flash receiver v0.2 and wearables v0.7 (ids 1-3) and run the checks under "To check on the hardware" in `Firmware/README.md`.
10. With receiver v0.2 and a v0.7 wearable, open `wearable_monitor`: move, punch, hold still and press the button, and check each row reacts; switch **Show Wearable** to the wearable's number.
