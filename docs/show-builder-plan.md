# Phases and placeholder events: plan

Written in ASD-STE100 Simplified Technical English.

Status: stage 1 is built (2026-11-19). Stages 2 and 3 are not built.

## 1. Purpose

Students make a dance piece in two stages:

1. They make the structure of the piece with simple placeholder shapes.
2. They replace the placeholders with real visuals.

The music, the phases and the inputs stay the same when a student replaces a placeholder.

## 2. Terms

| Term | Meaning |
|---|---|
| Phase | One part of the piece. A MIDI note of the song starts each phase. A piece has a maximum of 8 phases. |
| Event | One placeholder in a phase: a shape with a name in it. Each phase has a maximum of 8 events. |
| Trigger | The input that shows an event: a MIDI note of the song, or a hit or a button of a wearable. |
| Link | A continuous input that moves an event, for example the tilt of an arm or the position of the body. |
| Level | The panel setting that shows the tools step by step. |

## 3. How a student makes a piece (stage 1)

1. Load the song and its MIDI file.
2. Set the MIDI note that starts each phase.
3. In each phase, add the events. Give each event a name, for example "punch explode".
4. For each event, select the shape, the colour, the position and the size.
5. Select how the event shows, and select its trigger.
6. At Level 2, add links. A link moves an event while it is on the screen.
7. Play the song and dance.

## 4. Event settings

| Setting | What it does |
|---|---|
| On | Uses the event in the phase. |
| Name | The text in the shape. |
| Shape | Rectangle, circle or triangle. |
| Colour, X, Y, Size | The colour, the position and the size of the shape. |
| Show | Always: the event shows during all of the phase. Toggle: the trigger shows the event, and the trigger again hides it. For a time: the trigger shows the event for the time that you set. |
| Time | For a time: the number of seconds. A new trigger starts the time again. |
| Trigger, Note | A MIDI note of the song, or a hit or a button of wearable 1 to 3. |
| Link 1 and 2 | Movement: the continuous input. Moves: size, X, Y, rotation or brightness. From and To: the values at the two ends of the movement. |

Example: the dancer punches and a square shows. The dancer turns the arm and the square turns. The dancer punches again and the square goes away.

Settings for this example: Show = Toggle, Trigger = Wearable 1: hit, Link 1 = Wearable 1 roll, Moves = Rotation.

## 5. Rules

- Events fade in and fade out in 0.3 seconds.
- When the phase changes, the events of the new phase start hidden. Events with Show = Always fade in.
- A link continues from the current value of its input when its event shows again.
- Before the first phase note of the song, the piece is in phase 1.

## 6. Levels

| Level | What the panel shows |
|---|---|
| 1 | The music, the phases and the events with triggers. |
| 2 | Level 1 and the links. |
| 3 | Level 2. Later: the tools to replace the placeholders. |
| Advanced | All settings. |

## 7. Stages that are not built

**Stage 2: replace the placeholders.** For each event, the student selects a visual: the placeholder, an image or video, particles, noise, or a visual that the student makes. The trigger and the links stay the same.

**Stage 3: save and load a show.** One file keeps the phases and the events of a show. The student can then move the show to a new version of the toolkit.

## 8. Where it is

- Settings and logic: the `phases` component. The rules are in `phases/phase_logic.py`. The tests are in `tests/test_phases.py`.
- The shapes: the Phase Events instrument, `visuals/events`.
- The control panel: the Phases tab.
