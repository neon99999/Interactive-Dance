# Build your dance piece with phases: student guide

Written in ASD-STE100 Simplified Technical English. Spanish version: `guia-estudiantes-fases-es.md`.

## 1. The idea

You make your piece in steps:

1. Your song has parts. We call each part a **phase**.
2. In each phase, you put simple shapes on the screen. We call each shape an **event**. An event is a rectangle, a circle or a triangle with a name in it, for example "punch" or "jump".
3. Your movements show the shapes, hide the shapes and move the shapes.
4. Later, you change the simple shapes into real visuals.

You do not need to write code. You only change settings on the control panel.

## 2. Before you start

1. Open the project. The **Stage** window opens.
2. The control panel is on the right side of the Stage window. If you do not see it, push the **P** key.
3. At the top of the control panel, there are tabs: **Show**, **Phases**, **Instruments**, **Composition**, **Movement**, **Inputs**.
4. To change the language, click **English / Español** at the bottom right.
5. Click **Show**. Set **Level** to **Level 1**.

Tip: put the mouse on the name of a setting and wait. A short help text shows.

## 3. Level 1: phases and shapes

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

### 3.2 Add your first shape: always on screen

Example: during the calm start, a blue circle with the name "breathe" is always on the screen.

1. Set **Phase** to **Phase 1**.
2. Go down to **Event 1**.
3. Set **1 On** to **On**.
4. In **1 Name**, type `breathe`.
5. Set **1 Shape** to **Circle** and **1 Colour** to **Blue**.
6. Set **1 Show** to **Always**.
7. Click **Play** at the bottom of the Stage window. The circle shows on the screen.

### 3.3 Change the position and the size

- **X** moves the shape left and right. `-1` is the left edge, `0` is the center, `1` is the right edge.
- **Y** moves the shape down and up. `-1` is the bottom, `0` is the center, `1` is the top.
- **Size** makes the shape bigger or smaller.

Example: to put "breathe" at the top left, set **1 X** to `-0.5` and **1 Y** to `0.5`.

### 3.4 A shape that a movement shows: Toggle

Example: the dancer punches, and a red square shows. The dancer punches again, and the square goes away.

1. Go to **Event 2**. Set **2 On** to **On**.
2. In **2 Name**, type `punch`.
3. Set **2 Shape** to **Rectangle** and **2 Colour** to **Red**.
4. Set **2 Show** to **Toggle**.
5. Set **2 Trigger** to **Wearable 1: hit**.
6. Put on wearable 1 and punch. The square shows. Punch again. The square goes away.

### 3.5 A shape for a short time: For a time

Example: the dancer stomps, and a yellow triangle shows for 2 seconds.

1. Go to **Event 3**. Set it to **On**, name `stomp`, **Triangle**, **Yellow**.
2. Set **3 Show** to **For a time**.
3. Set **3 Time** to `2`.
4. Set **3 Trigger** to **Wearable 2: hit**.
5. Stomp. The triangle shows for 2 seconds. If you stomp again before the 2 seconds stop, the 2 seconds start again.

### 3.6 A shape on the music: MIDI note

Example: a white circle flashes on each drum beat of the song.

1. Go to **Event 4**. Set it to **On**, name `beat`, **Circle**, **White**.
2. Set **4 Show** to **For a time** and **4 Time** to `0.3`.
3. Set **4 Trigger** to **MIDI note (song)**.
4. In **4 Note**, type the MIDI note of the drum beat.
5. Play the song. The circle flashes on each beat.

### 3.7 What the settings mean

| Setting | What it does |
|---|---|
| On | Uses this event. Off: the event does not show. |
| Name | The word in the shape. Use a name for the movement, for example "punch". |
| Shape | Rectangle, Circle or Triangle. |
| Colour | The colour of the shape. |
| X, Y, Size | The position and the size of the shape. |
| Show | **Always**: on the screen during all of the phase. **Toggle**: the trigger shows it, the trigger again hides it. **For a time**: the trigger shows it for the number of seconds in **Time**. |
| Time | Only for **For a time**: the number of seconds. |
| Trigger | What shows the shape: **MIDI note (song)**, **Wearable 1-3: hit** (a fast movement) or **Wearable 1-3: button**. |
| Note | Only for **MIDI note (song)**: the number of the note. |

A grey setting has no effect with your current choices. For example, **Time** is grey when **Show** is not **For a time**.

### 3.8 Good to know

- Each phase has its own 8 events. Event 1 in Phase 1 and Event 1 in Phase 2 are different.
- When a new phase starts, the shapes of the old phase go away. **Always** shapes of the new phase come on.
- **Clear Phase** removes all the events of the phase that you see. Be careful: you cannot undo this.
- When the song moves to a new phase, the **Phase** setting moves too. Then you see the events of that phase.

## 4. Level 2: shapes that follow your body

Click **Show** and set **Level** to **Level 2**. Your work from Level 1 stays the same. Now each event has 2 **links**.

A link connects one movement of your body to one setting of the shape. The link works when the shape is on the screen.

### 4.1 Turn a square with your arm

Example: the dancer punches and the red square shows (from 3.4). Then the dancer tilts the arm, and the square turns.

1. Go to **Event 2** (the "punch" square).
2. Set **2 Link 1 Movement** to `serial_w1_roll`.
3. Set **2 Link 1 Moves** to **Rotation**.
4. Keep **2 Link 1 From** at `-180` and **2 Link 1 To** at `180`.
5. Punch to show the square. Tilt your arm to the left and to the right. The square turns.

### 4.2 Move a shape with your body position

Example: a circle follows the dancer from left to right on the stage. The camera must see the dancer.

1. Go to an event with **Show** set to **Always**.
2. Set **Link 1 Movement** to `pose_x`.
3. Set **Link 1 Moves** to **X position**.
4. Walk from the left side to the right side. The circle moves with you.

### 4.3 Two links on one shape

Example: the circle follows you (link 1, from 4.2), and it grows when you open your arms.

1. On the same event, set **Link 2 Movement** to `pose_spread`.
2. Set **Link 2 Moves** to **Size**.
3. Open and close your arms. The circle grows and gets smaller.

### 4.4 The movements

| Name in the menu | Your movement |
|---|---|
| `serial_w1_roll` (`w2`, `w3` for wearables 2 and 3) | Tilt the wearable to the side |
| `serial_w1_pitch` | Tilt the wearable up and down |
| `serial_w1_act` | How much you move (activity) |
| `serial_w1_gx`, `gy`, `gz` | How fast you twist, tilt or turn |
| `pose_x` | Your position, left to right (camera) |
| `pose_hand_l`, `pose_hand_r` | The height of your left or right hand (camera) |
| `pose_spread` | How wide you open your arms (camera) |
| `pose_energy` | How much your body moves (camera) |
| `camera_motion`, `camera_left`, `camera_right` | Movement in the camera image |

### 4.5 What the link settings mean

| Setting | What it does |
|---|---|
| Movement | The movement of the body that controls the shape. |
| Moves | What changes: **Size**, **X position**, **Y position**, **Rotation** or **Brightness**. |
| From | The value at the start of the movement (for example, arm tilted fully to the left). |
| To | The value at the end of the movement (for example, arm tilted fully to the right). |

Tip: if the shape moves in the wrong direction, change **From** and **To**. Example: From `180`, To `-180`.

## 5. Level 3

Level 3 is for the next step: you change the simple shapes into real visuals. This is not ready yet. Now, Level 3 shows the same as Level 2.

## 6. Save your work

Save your show at the end of each session.

1. Click the **Phases** tab.
2. In **Show File**, type a name with your name in it, for example `shows/ana_show.json`.
3. Click **Save Show**. **Show Status** shows "Saved ana_show.json".

To open your show again:

1. Type the same name in **Show File**.
2. Click **Load Show**. **Show Status** shows "Loaded ana_show.json".

The show file keeps your phases, your events, your song, your movement settings and your instrument settings.

When you change the **Level**, you do not lose work. The settings that you do not see stay the same.

## 7. If there is a problem

| Problem | What to do |
|---|---|
| The shape does not show. | Check that **On** is **On**. Check that **Phase** is the phase that plays now. Check that **Phase Events** is **On** (Composition tab). |
| The shape does not show when I move. | Check the **Trigger**. Check that the wearable is on and connected (Wearables window at the bottom of the Stage window). |
| The phase does not change with the song. | Check that **Follow MIDI** is **On**. Check the note in **Note for This Phase**. |
| The link does nothing. | Set **Level** to **Level 2**. Check that the shape is on the screen. For `pose_` movements, the camera must see you. |
| The computer is slow. | Ask the teacher. Turn off the instruments that you do not use (Composition tab). |
