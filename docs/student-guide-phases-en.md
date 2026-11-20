# Build your dance piece with phases: student guide

Written in ASD-STE100 Simplified Technical English. Spanish version: `guia-estudiantes-fases-es.md`.

## 1. The idea

You make your piece in steps:

1. Your song has parts. We call each part a **phase**. A piece has a maximum of 10 phases.
2. In each phase, you choose the instruments (Particles, Noise, Video Feedback, Shapes, Trigger Shape) and their settings.
3. You connect your movements to the instruments:
   - A **trigger** is a moment: a hit, a button press, a note of the song, entering a zone. Each time it happens, the Trigger Shape does something one time.
   - A **mapping** is continuous: while you move, a number changes, and it changes a setting all the time (for example, raise the arm and the particles get bigger).
4. Each phase keeps its own instrument settings, triggers and mappings. When the phase changes, everything changes with it.

You do not need to write code. You only change settings on the control panel.

## 2. Before you start

1. Open the project. The **Stage** window opens.
2. The control panel is on the right side of the Stage window. If you do not see it, push the **P** key.
3. At the top of the control panel, there are tabs: **Show**, **Phases**, **Instruments**, **Composition**, **Movement**, **Inputs**.
4. To change the language, click **English / Español** at the bottom right.
5. Click **Show**. Set **Level** to **Level 1**.

Tip: put the mouse on the name of a setting and wait. A short help text shows.

## 3. Level 1: phases, instruments and triggers

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

1. Click the picture in the Stage window (not the control panel).
2. Push a number key: **1** to **9** select phases 1 to 9. **0** selects phase 10.

The number keys do not work while you type in the control panel. Click the picture first.

### 3.3 Make the look of each phase

Example: the calm start has slow blue particles. The fast middle has fast particles and noise.

1. Set **Phase** to **Phase 1**.
2. Click **Composition**. In **Particles**, set **On** to **On**. Set **On** of the other instruments to **Off**.
3. Click **Instruments**. In **Particles**, set **Preset** to **Calm**. Change **Colour** if you want.
4. Set **Phase** to **Phase 2** (or push **2**). Phase 2 starts as a copy of phase 1.
5. Click **Composition**. In **Noise**, set **On** to **On**.
6. Click **Instruments**. In **Particles**, set **Preset** to **Energetic**.
7. Push **1**, then **2**. The look changes each time.

You do not need to save each phase. Each change is kept in the phase that you see.

The layers are always in the same order: Video Feedback at the back, then Noise, then Particles, then Shapes, and the Trigger Shape at the front. Parts of a layer that are dark let the layers below show through.

### 3.4 A trigger: a moment makes the Trigger Shape do something

Example: the dancer punches, and the shape jumps.

1. Click **Composition**. In **Trigger Shape**, set **On** to **On**.
2. Click **Movement**. Go to **Triggers**.
3. Set **1 On** to **On**.
4. Set **1 Source** to **Wearable 1**.
5. Set **1 Moment** to **Hit**.
6. Set **1 Does** to **Jump**.
7. Put on wearable 1 and punch. The shape jumps.

### 3.5 What a trigger can listen to

| Source | Moment |
|---|---|
| Song (MIDI) | A note of the song. Type its number in **Note**. |
| Wearable 1, 2 or 3 | **Hit** (a fast movement), **Button press**, **Becomes still** |
| Body (camera) | **Dancer appears**, **Enters zone 1** ... **Enters zone 5** |
| Test signals | **Test trigger** (for a test without a dancer) |

Zones: the camera picture is cut into strips from left to right (Inputs tab, **Stage Zones**). "Enters zone 2" happens one time, at the moment the dancer walks into zone 2.

### 3.6 What a trigger does

| Does | What happens |
|---|---|
| Pulse (grow) | The shape gets bigger for a short time. |
| Spin | The shape turns. **Amount** = degrees. |
| More sides | The shape gets more sides (or fewer). |
| Jump | The shape jumps to a new place. |
| Flash colour | The shape flashes in another colour. |

## 4. Level 2: mappings (movement changes a setting all the time)

Click **Show** and set **Level** to **Level 2**. Your work from Level 1 stays the same. Now the **Movement** tab also shows 8 **mappings**.

A mapping has four short menus:

| Menu | What you choose | Example |
|---|---|---|
| Source | Where the movement comes from | Wearable 1 |
| Input | Which movement of that source | Raise or lower the arm (pitch) |
| Instrument | Which instrument changes | Particles |
| Setting | Which setting of that instrument | Size |

The **Input** menu shows only the movements of the source that you chose. The **Setting** menu shows only the settings of the instrument that you chose.

### 4.1 Raise the arm, the particles get bigger

1. Click **Movement**. Go to **Mappings 1-4**.
2. Set **1 Source** to **Wearable 1**.
3. Set **1 Input** to **Raise or lower the arm (pitch)**.
4. Set **1 Instrument** to **Particles**.
5. Set **1 Setting** to **Size**. The mapping comes **On**.
6. Raise and lower your arm. The particles get bigger and smaller.

### 4.2 The noise follows you across the stage

1. Set **2 Source** to **Body (camera)**.
2. Set **2 Input** to **Position left-right**.
3. Set **2 Instrument** to **Noise** and **2 Setting** to **Speed**.
4. Walk from the left to the right. The noise moves faster. The camera must see you.

### 4.3 The movements

| Source | Input | Your movement |
|---|---|---|
| Wearable 1-3 | Turn the wrist (roll) | Turn the forearm, like you turn a key |
| Wearable 1-3 | Raise or lower the arm (pitch) | Arm down = low, arm forward = middle, arm up = high |
| Wearable 1-3 | Activity | How much you move |
| Wearable 1-3 | Twist / tilt / turn speed | How fast you turn the wearable |
| Wearable 1-3 | Still, Hit, Button | 1 while it happens, else 0 |
| Body (camera) | Position left-right, hand heights, arms spread, energy | Your body in the camera picture |
| Body (camera) | In zone 1-5 | 1 while you are in that zone, else 0 |
| Camera motion | Motion, left, right | Movement anywhere in the picture |

Tip: "Turn the wrist" does not work well when the arm points straight down or straight up. Use **Raise or lower the arm** for big arm movements.

### 4.4 More settings (Advanced)

At **Advanced**, each mapping also has **From**, **To**, **Smoothing** and **Sensitivity**:

- **From** and **To**: the setting's values at the two ends of the movement. If the setting moves in the wrong direction, change **From** and **To**.
- **Smoothing**: seconds the setting takes to follow the movement.
- **Sensitivity**: 2 = half of the movement reaches **To**.

## 5. Save your work

Your work is kept automatically: a few seconds after each change, the show is written to `shows/autosave.json`. When the project opens, it loads this file if it is newer than the project.

To keep a copy with your name:

1. Click the **Phases** tab.
2. In **Show File**, type a name with your name in it, for example `shows/ana_show.json`.
3. Click **Save Show**. **Show Status** shows "Saved ana_show.json".

To open your show again: type the same name in **Show File** and click **Load Show**.

The show file keeps your phases and their notes, the settings of each phase, the triggers and mappings of each phase, and your song.

## 6. Output to the projector

On the **Show** tab, in **Output**:

1. Set **Screen** to the projector (screen 1 is the main screen of the computer).
2. Keep **Borderless (Fill the Screen)** **On**.
3. Click **Open Output Window**. To close it, click **Close Output Window**.

**Level** makes all of the picture darker or brighter. **Saturation** makes the colours stronger (2) or black and white (0).

## 7. If there is a problem

| Problem | What to do |
|---|---|
| The number keys do nothing. | Click the picture in the Stage window first, then push the key. |
| An instrument does not show. | Check its **On** on the **Composition** tab, in the phase that plays now. |
| The trigger does nothing. | Check **On**, **Source** and **Moment**. Check that the Trigger Shape is **On**. Check that the wearable is on and connected (Wearables window at the bottom of the Stage window). |
| The mapping does nothing. | Set **Level** to **Level 2**. Check **Source**, **Input**, **Instrument** and **Setting**. For **Body** inputs, the camera must see you. |
| The phase does not change with the song. | Check that **Follow MIDI** is **On**. Check the note in **Note for This Phase**. |
| The computer is slow. | Ask the teacher. Turn off the instruments that you do not use (Composition tab). |
