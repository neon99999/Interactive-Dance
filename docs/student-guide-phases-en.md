# Build your dance piece with phases: student guide

Written in ASD-STE100 Simplified Technical English. Spanish version: `guia-estudiantes-fases-es.md`.

## 1. The idea

You make your piece in steps:

1. Your song has parts. We call each part a **phase**. A piece has a maximum of 10 phases.
2. In each phase, you choose the instruments that show (Media, Camera, Noise, Colour Tiles, Particles, Trigger Shape).
3. In each phase, you make 4 **connections**. A connection connects a movement of the dancer to an instrument.
   - A **movement** (raise the arm, walk across the stage) controls a setting all the time.
   - A **moment** (a hit, a button press, a note of the song, entering a zone) does something one time.
4. Each phase keeps its own instruments and connections. When the phase changes, everything changes with it.

You do not need to write code. You only change settings on the control panel.

## 2. Before you start

1. Open the project. The **Stage** window opens.
2. The control panel is on the right side of the Stage window. If you do not see it, push the **P** key.
3. At the top of the control panel, there are tabs: **Show**, **Phases**, **Composition**, **Movement**, **Inputs**.
4. To change the language, click **English / Español** at the bottom right.
5. Click **Show**. Make sure that **Level** is **Basic**.

Tip: put the mouse on the name of a setting and wait. A short help text shows.

## 3. Phases

### 3.1 Divide your song into phases

Example: your song has 3 parts. A calm start, a fast middle and a slow end.

1. Load your song and its MIDI file (ask the teacher for help).
2. Click the **Phases** tab.
3. Make sure that **Follow MIDI** is **On**.
4. Set **Phase** to **Phase 2**.
5. In **Note for This Phase**, type the MIDI note that starts the fast middle, for example `2`.
6. Set **Phase** to **Phase 3**. Type the note that starts the slow end, for example `1`.
7. Phase 1 starts at the start of the song. It does not need a note.

To find the note numbers, play the song and look at the **MIDI Notes** window at the bottom of the Stage window. If you do not know the notes, ask the teacher.

`-1` means "no note". A phase with `-1` does not start from the song.

### 3.2 Change phase with the number keys

Push a number key: **1** to **9** select phases 1 to 9. **0** selects phase 10.

The phase changes after a short time (less than half a second). When you type a number into a setting (for example a note), the phase does not change.

### 3.3 Choose the instruments of each phase

1. Set **Phase** to **Phase 1**.
2. Click **Composition**. Set **On** of each instrument that you want. Set the other instruments to **Off**.
3. For **Media**, click **Choose Folder...** and select a folder with pictures and videos.
4. Set **Phase** to **Phase 2** (or push **2**). Phase 2 starts as a copy of phase 1. Change it.
5. Push **1**, then **2**. The look changes each time.

You do not need to save each phase. Each change is kept in the phase that you see.

The instruments are always in the same order: Media at the back, then Camera, Noise, Colour Tiles, Particles, and the Trigger Shape at the front. Parts of an instrument that are dark let the instruments below show through.

## 4. Connections

Click **Movement**. Each phase has 4 connections. A connection has four menus:

| Menu | What you choose | Example |
|---|---|---|
| Source | Where the movement comes from | Wearable 1 |
| Input | The movement or the moment | Hit |
| Instrument | The instrument that changes | Whole picture |
| Does | What happens | Burst: Glitch |

The menus help you:

- **Input** shows only the inputs of the source that you chose.
- **Does** shows only what the instrument can do with that input.
  - For a movement, **Does** shows "Controls: ..." (the movement sets the value all the time).
  - For a moment, **Does** shows actions that happen one time: "Burst: ..." (the value jumps and falls back), and the instrument's own actions (Jump, Next file ...).
  - Some inputs are both (for example "In zone 1 / enters zone 1"). Then **Does** shows both.

When the four menus are set, the connection comes **On**.

### 4.1 Raise the arm, the particles get bigger (a movement)

1. Set **1 Source** to **Wearable 1**.
2. Set **1 Input** to **Raise or lower the arm (pitch)**.
3. Set **1 Instrument** to **Particles**.
4. Set **1 Does** to **Controls: Size**.
5. Raise and lower your arm. The particles get bigger and smaller.

### 4.2 Punch, and the picture glitches (a moment)

1. Set **2 Source** to **Wearable 1**.
2. Set **2 Input** to **Hit**.
3. Set **2 Instrument** to **Whole picture**.
4. Set **2 Does** to **Burst: Glitch**.
5. Punch. The picture glitches for a short time. **2 Amount** sets how strong.

### 4.3 Enter a zone, the next video plays (a moment)

1. Set **3 Source** to **Body (camera)**.
2. Set **3 Input** to **In zone 2 / enters zone 2**.
3. Set **3 Instrument** to **Media**.
4. Set **3 Does** to **Next file**.
5. Walk into zone 2. The next picture or video shows. The camera must see you.

### 4.4 A note of the song makes the shape jump

1. Set **4 Source** to **Song (MIDI)**.
2. Set **4 Input** to **A note of the song**. Type the note number in **4 Note**.
3. Set **4 Instrument** to **Trigger Shape** and **4 Does** to **Jump**.

### 4.5 The inputs

| Source | Input | Kind |
|---|---|---|
| Wearable 1-3 | Turn the wrist (roll), Raise or lower the arm (pitch), Activity, Twist / tilt / turn speed | Movement |
| Wearable 1-3 | Hit, Button press | Moment |
| Wearable 1-3 | Still / becomes still | Both |
| Body (camera) | Position left-right, hand heights, arms spread, energy | Movement |
| Body (camera) | In zone 1-5 / enters zone 1-5, Dancer seen / dancer appears | Both |
| Camera motion | Motion, left, right | Movement |
| Song (MIDI) | A note of the song | Moment |
| Test signals | Level, Zone (movement), Test trigger (moment) | For a test without a dancer |

Zones: the camera picture is cut into strips from left to right (Inputs tab, **Stage Zones**, Advanced).

Tip: "Turn the wrist" does not work well when the arm points straight down or straight up. Use **Raise or lower the arm** for big arm movements.

### 4.6 What the instruments can do

| Instrument | One-time actions (moments) | Controls (movements) |
|---|---|---|
| Whole picture | Burst of Brightness, Saturation, Glitch, Outline, Flash | The same settings |
| Trigger Shape | Pulse (grow), Spin, More sides, Jump, Flash colour | Size, position, rotation ... |
| Media | Play from the start, Next file, Random file | Position in the video, Opacity |
| Colour Tiles | Shuffle the colours | Gap, Scroll speed, Opacity |
| Particles, Noise, Camera | Burst of a setting | Each setting |

## 5. Save your work

Your work is kept automatically: a few seconds after each change, the show is written to `shows/autosave.json`. When the project opens, it loads this file if it is newer than the project.

To keep a copy with your name:

1. Click the **Phases** tab.
2. In **Show File**, type a name with your name in it, for example `shows/ana_show.json`.
3. Click **Save Show**. **Show Status** shows "Saved ana_show.json".

To open your show again: type the same name in **Show File** and click **Load Show**.

The show file keeps your phases and their notes, the instruments of each phase, the connections of each phase, and your song.

## 6. Output to the projector

On the **Show** tab, in **Output**:

1. Set **Screen** to the projector (screen 1 is the main screen of the computer).
2. Keep **Borderless (Fill the Screen)** **On**.
3. Click **Open Output Window**. To close it, click **Close Output Window**.

**Level** makes all of the picture darker or brighter. **Saturation** makes the colours stronger (2) or black and white (0).

## 7. If there is a problem

| Problem | What to do |
|---|---|
| The number keys do nothing. | Push one key and wait. Do not push other keys at the same time. |
| An instrument does not show. | Check its **On** on the **Composition** tab, in the phase that plays now. |
| A connection does nothing. | Check **On**, **Source**, **Input**, **Instrument** and **Does**. Check that the instrument is **On**. For wearables: check that the wearable is on and connected (Inputs tab, **Status**). For **Body** inputs: the camera must see you. |
| Media shows nothing. | Check **Folder** on the **Composition** tab. |
| The phase does not change with the song. | Check that **Follow MIDI** is **On**. Check the note in **Note for This Phase**. |
| The computer is slow. | Ask the teacher. Turn off the instruments that you do not use (Composition tab). |
