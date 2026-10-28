# Interactive Dance

TouchDesigner tools for interactive dance projects. The first is a simple toolkit for an interactive dance workshop. Participants choreograph movement and build interactive performances; the toolkit does the technical work of connecting music, sensors and visuals.

What it does:

- plays music and a MIDI file of events on one clock (play, pause, seek, reset)
- four visual layers: shapes, noise and ring textures, video or stills, and text, with simple effects
- a table that turns MIDI notes into visual actions (show, hide, toggle, trigger, fade, set value)
- a second table that maps movement signals onto visual values, with range and smoothing
- movement inputs: simulated controls, OSC, serial (USB) sensors, and camera motion

**Status:** all eight development milestones are done and tested inside TouchDesigner on Windows. Real sensors, a real webcam and macOS have not been tested yet; see [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md).

## Requirements

- [TouchDesigner](https://derivative.ca/download) 2025.32280 or later (the free Non-Commercial licence is enough)
- Tested on Windows 11. Nothing in the project is Windows-specific, but macOS is untested.

## Quick start

1. Clone or download this repository.
2. Open `TouchDesigner/DanceWorkshop.toe` in TouchDesigner.
3. Go into `project1` (double-click it). The **Dance toolkit - start here** box holds four components. Click one and press **P** to see its controls; press **I** to go inside.
4. On **transport**, turn **Play** on. The test track plays (a click every second, tones at 5, 10, 15 and 20 s) and the demo assignments show a circle at 5 s, double its size at 10 s, hide it at 15 s and flash the screen at 20 s.
5. To check a MIDI file against your music, watch **midi_monitor** next to the components: each note number flashes up as it plays.
6. On **visuals**, press **Open Output Window** (Output page) to show the result full screen.

The final image is `visuals/null_out`. It is also shown as the background of the `visuals` network.

## The four components

### transport: music and MIDI

| Control | What it does |
|---|---|
| **Audio File** | The music (WAV or MP3) |
| **MIDI File** | A Standard MIDI File (`.mid`) with the events for that music |
| **Play** | On plays, off pauses. Audio and MIDI always move together |
| **Reset** | Back to 0 seconds |
| **Seek To** + **Seek** | Jump to a position in seconds |
| **Position** / **Length** | Current position and track length (read-only) |

Only Note On messages are used: the note number (0-127) is what an assignment listens for. Velocity, channel and Note Off are ignored.

### engine: the assignment tables

On the **Assignments** page, **Edit MIDI Assignments** opens the MIDI table, which has up to 16 rows:

| note | target | action | value | duration |
|---|---|---|---|---|
| 60 | layer1 | show | | |
| 62 | layer1.scale | set | 2 | |
| 64 | layer1.opacity | fade | 0 | 2 |
| 65 | master.flash | trigger | 1 | 0.5 |

- **note**: the MIDI note number, 0-127.
- **target**: `layerN.value` or `master.value` (see below). A bare `layer1` means `layer1.visible`.
- **action**:
  - `show` / `hide` sets the value to 1 or 0.
  - `toggle` switches between 0 and 1.
  - `set` jumps to the value, or glides there over the duration if one is given.
  - `fade` glides to the value over the duration (seconds).
  - `trigger` holds the value for the duration (default 0.2 s), then returns to what it was.
- When two rows change the same target at the same moment, the **lower row wins**.

Layer values: `visible`, `opacity`, `red`, `green`, `blue`, `scale`, `x`, `y` (-1 to 1, 0 = centre), `rotate` (degrees), `content` (0 circle, 1 square, 2 triangle, 3 noise, 4 rings, 5 media, 6 text) and `effect` (0 none, 1 blur, 2 edges, 3 invert). Master values: `level`, `blackout`, `flash`.

Rows with a mistake are skipped, and the reason is listed under **Show Errors**. The rest keep working.

The look at any moment is worked out from the music position: every note before that point is replayed. So pausing never repeats an action, and seeking or Reset always shows the right state, including half-finished fades.

**Edit Input Assignments** opens the input table, which maps movement signals onto the same targets:

| signal | target | in_min | in_max | out_min | out_max | smoothing |
|---|---|---|---|---|---|---|
| sim_level | layer1.opacity | 0 | 1 | 0.2 | 1 | 0.3 |
| sim_zone | layer2 | | | | | |
| camera_left | layer3.scale | 0 | 0.3 | 1 | 2 | 0.5 |

- The signal is scaled from the in range to the out range and clamped. Blank ranges mean 0-1.
- **smoothing** is in seconds (0 = none).
- Input assignments are applied after MIDI ones, so a mapped input overrides the MIDI value for that target.
- They keep working while the music is paused.
- A signal that is not present (a sensor turned off or unplugged) is skipped, and the target falls back to its MIDI or starting value.

**Show Live Values** opens every value the engine is currently sending.

### inputs: movement signals

Every source adds signals to `inputs/signals`. Use their names in the input table.

| Page | Signals | Notes |
|---|---|---|
| **Simulated** | `sim_level` (0-1), `sim_trigger` (held button), `sim_zone` (on/off) | **Animate Level** moves `sim_level` on its own |
| **OSC** | one per OSC address: `/dancer/level` becomes `dancer/level` | Turn on **Receive OSC**; send to this computer on **OSC Port** (7000) |
| **Serial** | `serial_<name>` | Turn on **Read Serial**, pick the **Port** and **Baud Rate** |
| **Camera** | `camera_motion`, `camera_left`, `camera_right` | **Source**: Off, Camera or Test Pattern. Raise **Sensitivity** if values stay small |

Serial devices should print one line per reading, in either of these forms:

```
accel=0.52, zone=1        name=value (or name:value) pairs -> serial_accel, serial_zone
0.52,1                    plain numbers (comma, space or ;) -> named by Value Names, e.g. "accel, zone"; otherwise serial_1, serial_2
```

Pieces that are not numbers are skipped. The values hold until the next line arrives.

The camera input measures how much the picture changes between frames, over the whole image and over the left and right halves. To use a value as an on/off zone, give it a narrow in range, e.g. `camera_left`, in 0.05-0.06, out 0-1.

**Body tracking:** for skeleton tracking, the [MediaPipe TouchDesigner plugin](https://github.com/torinmb/mediapipe-touchdesigner) by Torin Blankensmith and Dom Scott is a good fit. It runs MediaPipe inside TouchDesigner with no separate install. It is not included here. To use it, download `release.zip` from its releases page, drag `MediaPipe.tox` into `inputs`, add a Select CHOP that picks the channels you want (e.g. a wrist position), and wire it into `merge_signals`. Those channel names then work in the input table.

### midi_monitor: check your MIDI file

A panel next to the other components. While the music plays it shows the number of each MIDI note as it happens, large, with the background flashing on each new note, so you can see at a glance whether the notes land where you expect in the music. The line below shows the note names (60 = C4; Ableton calls the same note C3) and the playback time.

- **Hold Time** (Monitor page): how long each note stays on screen, 1.5 s by default. Notes played together are shown together.
- Like the engine it follows the playback position, so pausing, seeking and Reset show the notes due at that point.
- The numbers are the ones to use in the MIDI assignment table.
- To see it bigger, right-click it and choose **View...**.

### visuals: four layers

`visuals/layer1` to `layer4` each have a **Layer** page with the starting look:

- **Visible**, **Opacity**, **Color**, **Scale**, **X**, **Y**, **Rotate**
- **Content**: circle, square, triangle, noise, rings, media or text
- **Effect**: none, blur, edges or invert
- **Media File**: a movie or still image, used when Content is media
- **Text**: used when Content is text

Assignments change these values while the show runs. Layer 4 is on top. The visuals component itself has **Level**, **Blackout** and **Flash** for the whole image, and **Open/Close Output Window**.

`layer2`-`layer4` are clones of `layer1`: they share its network but keep their own settings. Edit the network inside `layer1` only.

## Testing

The automatic tests run inside TouchDesigner, take under a minute and leave your tables and settings as they were. Open the Textport (**Alt+T**) and run:

```python
op('/project1/tests/engine_tests').module.Run()
```

Results appear in `project1/tests/results` (63 checks): MIDI actions, conflicts, pause, seek, reset, real playback, invalid rows, rendered pixels for every content type and effect, four layers, simulated inputs, OSC, serial lines and the camera test pattern.

The plain-Python unit tests (show logic and the serial parser) need no TouchDesigner:

```
python -m unittest discover -s tests -v
```

`project1/test_t01` is the original audio/MIDI sync test: `op('/project1/test_t01/sync_test').module.Start()`.

The test media in `media/test/` is generated by `tools/make_test_media.py` (standard library only).

## Repository layout

```
TouchDesigner/
  DanceWorkshop.toe        the project; open this
  project1/
    transport.tdxn         music + MIDI clock
    engine.tdxn            assignment tables and the engine
    engine/show_logic.py   the rules (pure Python, unit-tested)
    inputs.tdxn            movement signals
    inputs/serial_parse.py serial line parser (pure Python, unit-tested)
    visuals.tdxn           layers, compositing, output
    midi_monitor.tdxn      shows MIDI notes as they play
    tests.tdxn, tests/     in-TouchDesigner tests
Firmware/                  wearable motion sensor firmware (PlatformIO, see Firmware/README.md)
media/test/                test audio, MIDI and image
tests/                     plain-Python unit tests
tools/                     helper scripts
DEVELOPMENT_STATUS.md      what is done, tested, untested and known
```

The components are saved as text (`.tdxn` and `.py`) by [Embody](https://github.com/dylanroscover/Embody), so changes show up clearly in git. `CLAUDE.md`, `AGENTS.md` and `.claude/` hold instructions for AI coding assistants working on the project.
