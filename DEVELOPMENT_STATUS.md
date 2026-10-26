# Development status

Last updated 2026-10-26.

**Latest working project:** `TouchDesigner/DanceWorkshop.toe`, at git commit `f8df998` or later on `main`. It was saved, reopened and retested: all 63 checks pass. Commits after Task 01 are local only; nothing has been pushed since `6627104`.

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

**Plain Python:** `python -m unittest discover -s tests`: **32 of 32** pass (25 show logic, 7 serial parser). 2000 notes evaluate in under 1 ms.

**Save/reopen:** TouchDesigner was relaunched on the saved project; there were no errors, pages, tables and annotations were intact, and all 63 checks passed.

**Task 01 sync test:** `op('/project1/test_t01/sync_test').module.Start()` (passed when Task 01 was done).

## Not verified (needs a person or hardware)

- **Listening:** the audio lags the visuals by the output buffer (about 0.15 s, more over remote desktop). Not measured by ear, and there is no latency setting yet.
- **Movies:** Content "media" was tested with a still image. A movie plays on its own clock, not synced to the music, seek or pause.
- **Real serial device:** no hardware was connected. Lines were fed to the same callback the Serial DAT uses.
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

1. Play the test track and listen: do the visual events line up with the tones at 5, 10, 15 and 20 s?
2. Put a movie in `layer1` (Content media, Media File) and check playback and performance.
3. Send OSC from a phone or another computer to port 7000, e.g. `/dancer/level 0.5`, with **Receive OSC** on.
4. Connect an Arduino that prints `accel=0.5` lines; pick the port and baud; map `serial_accel`.
5. Plug in a webcam, set Camera **Source** to Camera, wave left and right, and watch `camera_left` / `camera_right`.
6. Open the project on a Mac and run the tests.
7. Press the Assignments buttons on `engine` and the Output buttons on `visuals`.
