# Show Builder: plan

Status: plan for review. Nothing in this plan is built yet.
Written in ASD-STE100 Simplified Technical English.

## 1. Purpose

The toolkit shows how the parts work. But students cannot easily make their own show with it.

The Show Builder lets a student make a dance piece in two steps:

1. Make the structure of the piece with simple placeholder visuals.
2. Replace each placeholder with a better visual.

The connections stay the same when the student replaces a visual. The MIDI notes, scene changes, sensors and camera continue to control the new visual.

## 2. Terms

| Term | Meaning |
|---|---|
| Element | One named part of the show, for example "Rain" or "Heartbeat". A show has a maximum of 8 elements. |
| Control | One of the 9 standard values of an element (see section 4). |
| Placeholder | The simple visual that an element shows first: a shape with the name of the element on it. |
| Visual | What the element shows: the placeholder, a ready-made visual, or a visual that the student makes. |
| Scene | One section of the piece. A scene has its own connections. A show has a maximum of 8 scenes. |
| Connection | One row that links an input to a control of an element. |
| Input | A source of data: a MIDI note of the song, a wearable sensor, the camera. |
| Show file | One file that keeps the elements, scenes and connections of a show. |

## 3. How a student makes a show

1. Load the song and its MIDI file.
2. Add the elements of the piece. Give each element a name and a colour.
3. Make the scenes. Set the MIDI note that starts each scene.
4. In each scene, add the connections. For example: "wrist hit fires Explosion".
5. Play the song. Dance. Adjust the connections.
6. Save the show file.
7. Replace the placeholders with visuals, one element at a time.
8. Play the song again. The connections do not change.

The student can do steps 1 to 6 on day one, without knowledge of visuals.

## 4. The controls of an element

Each element has the same 9 controls:

| Control | Range | What it does |
|---|---|---|
| Visible | on or off | Shows or hides the element. |
| Opacity | 0 to 1 | Sets how transparent the element is. |
| Size | 0 to 2 | Sets the size. 1 is the normal size. |
| X, Y | -1 to 1 | Sets the position. 0, 0 is the centre. |
| Rotate | -180 to 180 | Turns the element, in degrees. |
| Colour | 0 to 1 | Sets the tint, around the colour wheel. |
| Amount | 0 to 1 | A general value. Each visual uses it in its own way, for example speed or brightness. |
| Fire | event | A moment, for example a hit or a beat. Each visual uses it in its own way. |

The compositor applies Visible, Opacity, Size, X, Y and Rotate to all visuals. Thus a new visual works immediately. The visual itself uses Amount, Fire and Colour.

Decision to make: add a second general value, Amount 2, for visuals that need two values.

## 5. The placeholder

Each new element shows a placeholder:

- A shape: circle, triangle, square or polygon. The student selects the shape and the colour.
- The name of the element, written on the shape.
- Amount makes the shape brighter and more filled.
- Fire makes the shape flash and pulse.

The placeholder uses the Trigger Shape instrument that is in the toolkit now.

During rehearsal, a label below each element shows its connections, for example "RAIN ← wrist activity". The Labels switch on the stage turns the labels off for the performance.

## 6. Scenes

- A show has a maximum of 8 scenes. The student gives each scene a name, for example "Intro" or "Storm".
- A scene starts when the song plays a MIDI note that the student selects for that scene. The student can also select a scene by hand.
- Each scene has its own connections.
- Each scene can also keep a look: which elements are visible, and their start values. The "Keep look" button stores the current values in the scene.
- The stage shows the name of the current scene.

The scenes replace the presets A to D.

## 7. Connections

A connection has 3 parts: an input, an element control and a behaviour.

### 7.1 Inputs

| Input | Type |
|---|---|
| MIDI note of the song (note number) | event |
| Wearable 1 to 3: hit, button | event |
| Wearable 1 to 3: activity, tilt, still | value |
| Camera: movement, hand height, body position | value |

### 7.2 Behaviours for events

| Behaviour | What it does to the control |
|---|---|
| Fire | Sends a Fire event to the element. |
| Set | Sets the control to a value. |
| Random | Sets the control to a random value between two limits. |
| Step | Adds a value to the control. |
| Pulse | Moves the control to a value, then back. |
| Show, Hide, Toggle | Changes Visible. |

### 7.3 Behaviour for values

| Behaviour | What it does to the control |
|---|---|
| Follow | The control follows the input. The student sets the input range, the output range and the smoothing. |

These are the mapping rows and trigger rows of the toolkit now, but they point at element controls.

## 8. Replace a placeholder

The student selects a different visual for the element from a menu:

| Visual | Amount does | Fire does |
|---|---|---|
| Placeholder | Fills the shape | Flash and pulse |
| Particles | Particle energy | A burst |
| Noise | Movement speed | A jump in the pattern |
| Video (camera) | Effect strength | A freeze frame |
| Media (new) | Fade level | Next image or video, or random |
| My visual | The student decides | The student decides |

### 8.1 The Media visual (new)

The Media visual plays the images and videos in a folder. It has these settings:

- Folder
- On Fire: Next, Random or Restart
- Fade time
- Play once or loop

### 8.2 My visual (the template)

1. Select "My visual" for an element. The toolkit makes a copy of the template.
2. Open the template. It contains:
   - an Out TOP named `out1`, which the compositor shows;
   - a CHOP named `element`, with these channels: `visible`, `opacity`, `size`, `x`, `y`, `rotate`, `colour`, `amount` and `fire`. The `fire` channel is 1 for one frame at each Fire event.
3. Make the visual with operators. For example, connect `fire` to a Count CHOP, and the count to a Switch TOP.
4. Use Python only if necessary. Python is not necessary for most visuals.
5. Save the visual as a `.tox` file in the `my_visuals` folder.

The toolkit loads the `my_visuals` folder when it starts. Thus the student keeps the visuals when the toolkit gets an update.

## 9. The Show tab

The Show tab is a new tab in the control panel. It has 3 parts:

```
+-------------------------------------------------------------+
| SHOW: My Piece                   [Save Show] [Load Show]    |
+-------------------------------------------------------------+
| ELEMENTS                                                    |
|  1 Rain       blue   circle    Visual: [Placeholder v]      |
|  2 Heartbeat  red    square    Visual: [Particles   v]      |
|  3 Explosion  white  triangle  Visual: [Media       v]      |
|  [+ Element]                                                |
+-------------------------------------------------------------+
| SCENES                                                      |
|  1 Intro   note 36   [Keep look]                            |
|  2 Storm   note 38   [Keep look]                            |
|  [+ Scene]                                                  |
+-------------------------------------------------------------+
| CONNECTIONS in scene: [Storm v]                             |
|  Wearable 1 hit       -> Explosion Fire                     |
|  Wearable 2 activity  -> Rain Amount   Follow 0-1, smooth   |
|  MIDI note 60         -> Heartbeat Fire                     |
|  [+ Connection]                                             |
+-------------------------------------------------------------+
```

For students, the Show tab replaces the Movement tab and the trigger rows. The old tabs stay available in Advanced mode.

Decision to make: is the Show tab in the control panel, or in a separate window? The control panel is the first choice.

## 10. Show file and updates

- Save Show writes one file, for example `shows/my_piece.json`. The file keeps the elements, the scenes, the connections, the scene looks, the song and the MIDI file.
- Load Show reads the file and sets all of the show again.
- The visuals that a student makes are in `my_visuals`, not in the show file.

To give students an update:

1. The student pushes Save Show.
2. The student extracts the new zip file next to the old one.
3. The student copies the `shows` and `my_visuals` folders into the new copy.
4. The student opens the new copy and pushes Load Show.

## 11. Example piece

A solo of 3 minutes, with 1 wearable on the right wrist.

| Scene | MIDI note | Connections |
|---|---|---|
| Intro | 36 | Wrist activity -> Rain Amount (Follow). |
| Storm | 38 | Wrist hit -> Explosion Fire. Song note 60 -> Heartbeat Fire. Camera movement -> Rain Size (Follow). |
| End | 40 | Wrist still -> Rain Opacity (Follow, inverted). Explosion hidden. |

Day one: the 3 elements are placeholders. The dancer rehearses the full piece.
Day three: Rain becomes Particles, Explosion becomes Media with a folder of photos, and Heartbeat becomes the student's own visual. The connections do not change.

## 12. What stays and what changes

Stays:

- The engine, the MIDI reading, the inputs and the wearables.
- The instruments: Particles, Noise, Video and Trigger Shape. They become visuals that an element can use.
- The MIDI table and the Advanced mode, for teachers and advanced students.

Changes:

- The compositor gets 8 slots, one for each element. Now it has 4 slots.
- The compositor applies Size, X, Y and Rotate to all visuals.
- The scenes (8) replace the presets A to D.
- The connections point at element controls.

## 13. Build order

Each step ends with tests and a check on LAPTOP.

1. Elements and placeholders. The 9 controls. The compositor with 8 slots and the transform. About 1 session.
2. Scenes and connections. All behaviours, Fire included. The labels on the stage. About 1 session.
3. The visual menu, the Media visual and the template for My visual. The `my_visuals` folder. About 1 session.
4. Save Show and Load Show. The student package with the `shows` and `my_visuals` folders. Less than 1 session.

After step 2, the students can make a full show with placeholders.

## 14. Limits

- A maximum of 8 elements. More elements use more of the graphics card. Measure the frame rate on LAPTOP with 8 visuals.
- A maximum of 8 scenes.
- A Fire event that comes in a scene change goes to the new scene.
- The show file does not keep the visuals that a student makes. These stay in `my_visuals`.

## 15. Decisions to make

1. Add Amount 2: yes or no.
2. The Show tab: in the control panel or in a separate window.
3. The number of scenes: 8 or more.
4. The labels below the elements: on by default during rehearsal, yes or no.
