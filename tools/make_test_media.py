"""Generate the Task 01 sync test files: media/test/sync_test.wav and sync_test.mid.

Audio: a quiet click on every whole second (so position is audible), plus a
sine tone at the pitch of each MIDI note, starting exactly when the note does.
MIDI: format 0, 120 BPM, 480 PPQ, so 1 second = 960 ticks.

Run with the full interpreter path, e.g.
  .../Python312/python.exe tools/make_test_media.py
"""
import math
import struct
import wave
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "media" / "test"
DURATION = 30.0          # seconds
RATE = 44100
NOTE_LEN = 0.5           # seconds each note sounds
PPQ = 480
TEMPO_US = 500_000       # microseconds per quarter note = 120 BPM
TICKS_PER_SEC = PPQ * 1_000_000 // TEMPO_US

# (time in seconds, MIDI note number)
NOTES = [(5, 60), (10, 62), (15, 64), (20, 65), (20, 67)]


def midi_hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def make_wav(path):
    total = int(DURATION * RATE)
    buf = [0.0] * total
    # Click: 5 ms 2 kHz burst each second (louder on 0, 5, 10 ...).
    for s in range(int(DURATION)):
        amp = 0.35 if s % 5 == 0 else 0.15
        start = s * RATE
        for i in range(int(0.005 * RATE)):
            buf[start + i] += amp * math.sin(2 * math.pi * 2000 * i / RATE)
    # Note tones, with 10 ms fade in/out to avoid pops.
    fade = int(0.01 * RATE)
    for t, n in NOTES:
        start, length = int(t * RATE), int(NOTE_LEN * RATE)
        hz = midi_hz(n)
        for i in range(length):
            env = min(1.0, i / fade, (length - i) / fade)
            buf[start + i] += 0.3 * env * math.sin(2 * math.pi * hz * i / RATE)
    frames = b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 32767)) for v in buf)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames)


def vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def make_mid(path):
    events = []  # (tick, order, bytes); Note Off sorts before Note On at the same tick
    for t, n in NOTES:
        on = int(t * TICKS_PER_SEC)
        off = int((t + NOTE_LEN) * TICKS_PER_SEC)
        events.append((on, 1, bytes([0x90, n, 100])))
        events.append((off, 0, bytes([0x80, n, 0])))
    events.sort()
    track = vlq(0) + b"\xFF\x51\x03" + TEMPO_US.to_bytes(3, "big")
    track += vlq(0) + b"\xFF\x58\x04\x04\x02\x18\x08"  # 4/4
    last = 0
    for tick, _, data in events:
        track += vlq(tick - last) + data
        last = tick
    end = int(DURATION * TICKS_PER_SEC)
    track += vlq(end - last) + b"\xFF\x2F\x00"
    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, PPQ)
    path.write_bytes(header + b"MTrk" + struct.pack(">I", len(track)) + track)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    make_wav(OUT / "sync_test.wav")
    make_mid(OUT / "sync_test.mid")
    print("wrote", OUT / "sync_test.wav", "and", OUT / "sync_test.mid")
