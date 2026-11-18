# Changing the hit sensitivity

The wearable decides what counts as a **hit** itself, so the setting lives in the firmware. Changing it means editing one line and flashing the wearables again (on LAPTOP, about 1 minute per wearable). Nothing changes in TouchDesigner.

## 1. Pick the number to change

Open `Firmware/include/config.h` and find these two lines (around line 100):

```cpp
constexpr ModeSettings WRIST_SETTINGS = {"wrist", 1.5f, 600.0f, 1.5f, 0.04f};
constexpr ModeSettings ANKLE_SETTINGS = {"ankle", 2.5f, 500.0f, 3.0f, 0.04f};
```

The **fourth number** is the hit threshold in g: how hard the wearable must be jolted for a hit.

| Mode | Now | Less sensitive (fewer hits, needs a harder move) | More sensitive |
|---|---|---|---|
| Wrist | `1.5f` | `2.0f`, then `2.5f` | `1.2f` |
| Ankle | `3.0f` | `3.5f`, then `4.0f` | `2.5f` |

- Change only the mode the dancers use (the receiver's display and wearable_monitor show WRIST or ANKLE).
- Go up in steps of 0.5 and test after each one.
- Keep the `f` at the end of the number.

**Two hits from one move** (for example the punch and then the stop): raise `HIT_WINDOW_MS` a few lines above, from `250` to `350`. Everything inside that time counts as one hit.

## 2. Flash the wearables (LAPTOP)

1. Plug in one wearable by USB and switch it on.
2. In a terminal in the `Firmware` folder (or with the PlatformIO buttons in VS Code), run the line for that wearable:

   ```
   pio run -e wearable -t upload     # wearable 1
   pio run -e wearable2 -t upload    # wearable 2
   pio run -e wearable3 -t upload    # wearable 3
   ```

   Each wearable has its own line, because each one has its own id. Using the wrong line gives two wearables the same id (the receiver shows `DUP`).
3. Unplug it, and keep it still for a second after switching it on (it calibrates).
4. Repeat for the other wearables.

If it does not flash: close any serial monitor and TouchDesigner's **Read Serial** (only one program can use the port), or hold BOOT while pressing RESET and try again.

## 3. Check it

1. In TouchDesigner, turn on **Inputs > Read Serial** and look at **wearable_monitor**.
2. Do the move the dancers will do: the **hit** lamp should light for real hits and stay off for ordinary steps or arm swings.
3. Too many hits: raise the number again. Real hits missed: lower it.
4. Write the values that worked into `config.h` for good, and commit and push, so the next build keeps them.
