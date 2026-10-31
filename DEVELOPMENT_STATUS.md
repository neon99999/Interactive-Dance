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
| 10 | Body tracking with MediaPipe (inputs, Pose page) | `5d007ba` | Built 2026-10-29. Confirmed by the user on LAPTOP with a webcam (2026-10-29) |
| 11 | Stage zones, `pose_monitor`, mapping page with presets, MIDI preset switching, English/Spanish (`lang`) | `fa157fa` | Built 2026-10-29 (overnight, MINI-PC). Confirmed by the user on LAPTOP with a webcam (2026-10-29); Spanish texts still need a native speaker's review |

## Tests

**In TouchDesigner:** run `op('/project1/tests/engine_tests').module.Run()`. Results go to `tests/results`; the last run (2026-10-29, MINI-PC, with the mapping checks) passed **79 of 79**.

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
- **mappings (14):** a mapping page preset drives a visual; a MIDI row `set mapping.preset 2` switches to preset B at its note and a later row back to A (also when seeking); Follow MIDI off ignores them; choosing a Visual fills in its natural From/To and writes the engine row; the Preset menu; Spanish labels and menus and back to English; pose_monitor has no errors and all its values.

The suite backs up and restores the mapping page and the language, and empties the mapping presets while it runs (their rows would override the values under test).

**Plain Python:** `python -m unittest discover -s tests`: **81 of 81** pass (27 show logic, 10 serial parser including the receiver's v0.2 line format, 13 motion model, 20 body tracking including stage zones, 11 mapping page). 2000 notes evaluate in under 1 ms.

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

## Verified on hardware (2026-10-29, LAPTOP)

- **Wearable fw v0.7, button and motor:** on a breadboard over USB, the button on D1 reads `btn=1` while held and a 1.5 s hold switches wrist/ankle (`[mode]` line, `mode` value). The motor on D2 (NPN transistor) buzzes twice for ankle and once for wrist, from the button and from `a`/`w`. Lying flat: gyro calibrated, `still=1`, pitch and roll about -1 deg; activity noise 0.012 (ankle) / 0.020 (wrist), half the still threshold. Hits, ESP-NOW with v0.7 and receiver v0.2 still to test.

## Verified on hardware (2026-10-30, LAPTOP)

Reported by the user on the Project Hub checklist:

- **Receiver v0.3:** flashed; the boot screen shows the yellow logo and `RX v0.3`, and the old v0.5 wearable still shows LIVE.
- **Wearable 1 on v0.8:** flashed; gyro calibrated, the display row shows the version and mode, and the rate is about 104 a second. All six hit directions are correct. Activity, hit, still, ankle mode, the button and the motor all behave.
- **Still to do:** flash wearables 2 and 3, run all three together (frame rate, `wearable_monitor`), measure the battery divider and make the tuning recordings.

## Battery reading (2026-10-30, not yet on hardware)

- **Hardware:** one battery is wired and powers its wearable. The divider on all three is 200k from switched BAT+ to A0 and 100k from A0 to GND, ratio 3.0, on D0/A0 (GPIO0).
- **Wearable v0.9:** reads A0, smooths it, works out a rough percentage and sends a Battery packet every 5 s. Protocol stays v3, so boards can be flashed in any order. Each changed file compiles with no warnings using the C6 toolchain directly; it has not been linked, because PlatformIO on MINI-PC refuses the platform. Build it on LAPTOP.
- **Receiver v0.4:** compiles with no warnings. Shows the percentage on the display, in place of roll, and prints `w1_batt` and `w1_battv`, which reach TouchDesigner as `serial_w1_batt` and `serial_w1_battv`. No TouchDesigner change was needed; the parser test covers the new line.

## Cali venue (2026-10-30, from the user)

- **Projection:** on the walls, with 3 projectors (2 from the venue, 1 borrowed).
- **Cameras:** 3 of our own Logitech C920 HD webcams; tripods requested from the venue.
- **Audio:** speakers requested for each computer, plus a proper playback system for the performance.
- **Room:** stage size is no concern; power near the equipment, the room can be darkened, and internet is available.
- **Two parts:** class experiments in 3 groups, then a performance. The 3 projectors, webcams and computers with speakers are for the groups; one laptop runs the final show.
- **Still to get:** photos or a plan of the room.

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
- **Body tracking (MediaPipe), 2026-10-29, MINI-PC:** the MediaPipe TouchDesigner plugin v0.6.0 loads on TD 2025.32280 (`inputs/mediapipe`, from the git-ignored `TouchDesigner/toxes/`; only pose detection on, and it cooks only while Pose **Source** is Camera). `pose_signals.py` turns the landmarks into `pose_present`, `pose_x`, `pose_hand_l`, `pose_hand_r`, `pose_spread`, `pose_energy`, measured in torso lengths (estimated from the shoulders when the hips are out of the picture); `tests/test_pose_signals.py` (16 tests). The chain was checked with the plugin's leftover sample landmarks and with the Test Dancer through `signals`; `pose_chop` costs about 0.3 ms per frame. Not yet tried with a webcam: there is none on MINI-PC. The plugin's Webcam menu fills from the cameras the browser finds once it runs.
- **Tests now leave the visuals as they were:** the render tests reset every layer to its defaults and never put them back, and the engine tests assumed default layers, so with `layer1` **Visible** on two engine checks failed. The suite now backs up the visuals' layer and master settings, starts from the defaults, and restores them at the end (checked: 65 of 65 pass with `layer1` Visible on, and it stays on).
- **Tests now restore the inputs' settings:** the input tests used to leave Serial, OSC, Simulated and Camera switched off and the serial values cleared; the tests now back them up and put them back (checked: settings and serial values identical after a run, 63 of 63 pass).

## Built overnight 2026-10-29 (MINI-PC), confirmed on LAPTOP 2026-10-29

The user ran manual tests 11-14 on LAPTOP with the webcam and reported that all of them work.

- **Stage zones** (inputs, Pose page): **Stage Zones** 1-5 (default 3) and **Zone Margin** (default 0.05 of the picture width, a hysteresis band so standing on a border does not flicker). New signals `pose_zone` (1..N, 0 when nobody is seen) and `pose_zone1` ... `pose_zone5`, from the smoothed `pose_x`, so Flip Left/Right flips them too.
- **`pose_monitor`** panel: MediaPipe's camera picture with the zones drawn over it (borders, margin bands), the dancer's position line, our own skeleton from the landmarks the signals use, a zone strip under the picture lighting the current zone, and bars for position, hands, spread and energy. Checked by captured frames with the Test Dancer (no webcam on MINI-PC). Cost while on screen about 3 ms CPU + 1.4 ms GPU per frame on MINI-PC; nothing while not shown.
- **`mappings`** (the mapping page): 8 slots (On, Movement, Visual, From, To, Smoothing, Sensitivity), presets A-D with starter presets, Copy/Clear. Its rows go to the engine after the input table. The Visual menu comes from the engine's `knownParams()`, so new visual values show up by themselves. A MIDI row `set mapping.preset 1-4` switches presets during the song (new engine value `mapping.preset`, replayed like any other on seek). Found and fixed while testing: Parameter Execute callbacks arrive a frame after a preset loads, which had reset From/To to the natural range on every preset switch; a change is now judged against the stored preset.
- **`lang`**: **Language / Idioma** switches the Pose page, the mapping page (labels, help, menus) and pose_monitor between English and Spanish, from `lang/strings` (key, en, es). The Spanish texts were written by Claude and should be read by a Spanish speaker before the workshop.
- **Wearable enclosure (Fusion 360, from the enclosure session):** parametric model done, 74.4 × 40.5 × 18.7 mm with a 2 mm lid; battery pocket for the measured 59.2 × 26.5 × 9.7 mm cell; the motor (10 mm × 3.2 mm, still a placeholder box) stands against the end wall; a 1.5 mm shelf screwed to two rails holds the XIAO, IMU and button, with a 4 mm wire slot; three parametric test pieces (battery pocket, insert hole, button hole). Open: which end of the battery the lead exits (decides the wire slot) and which edge of the XIAO has the BAT+/BAT− pads. Not started: printing the test pieces, a fit check, final parameter names and a parts list.

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
- A timeout that drops stale sensor values.
- A friendlier editor than the table viewers.
- More wearable signals: `spin` (a sustained turn) and `jump` (brief weightlessness, reliable on the ankle only).

## Dependencies

- TouchDesigner 2025.32280 or later. The project uses only native operators and no extra Python packages.
- Body tracking only: the MediaPipe TouchDesigner plugin v0.6.0, downloaded once per computer into `TouchDesigner/toxes/` (see README).
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
8. On the wearable, confirm the pins and test the button, vibration motor and battery reading (`Firmware/README.md`, Battery).
9. Flash receiver v0.4 and wearables v0.9 (ids 1-3) and run the checks under "To check on the hardware" in `Firmware/README.md`.
10. With receiver v0.4 and a v0.9 wearable, open `wearable_monitor`: move, punch, hold still and press the button, and check each row reacts; switch **Show Wearable** to the wearable's number.
11. ~~On LAPTOP, install the MediaPipe plugin (README, Body tracking), set Pose **Source** to Camera (MediaPipe), pick the webcam, and check each `pose_*` signal: walk left and right, raise each hand, spread the arms, move fast and stand still. Check that `pose_hand_l` follows your own left hand.~~ (done 2026-10-29, LAPTOP).
12. ~~On LAPTOP with the webcam, open `pose_monitor` (right-click > View...): check our skeleton sits on MediaPipe's drawing, walk through the zones and watch the strip and `pose_zone` change without flicker on a border, and try **Stage Zones** 2-5 and **Flip Left/Right**.~~ (done 2026-10-29, LAPTOP).
13. ~~On `mappings`, try the starter presets A-D with the Test Dancer and then a real dancer; add a MIDI row `set mapping.preset 2` and check the switch lands at its note.~~ (done 2026-10-29, LAPTOP).
14. Switch **Language / Idioma** to Español (switch works, 2026-10-29) and have a Spanish speaker read the Pose page, the mapping page and pose_monitor (`lang/strings.tsv`, `es` column).
15. Before the workshop: start the mapping page empty, or with a preset made for the workshop (preset A is active for testing now).
