"""Fire MIDI Note On events from midiin_notes as the shared clock passes them.

midiin_notes holds the whole MIDI file as a fixed clip (one channel per note,
1 while the note is held). Each frame this scans the clip between the previous
and current clock position for notes switching on, so simultaneous notes and
notes shorter than a frame are all caught. Nothing fires while paused, after a
backward jump, or after a Reset/Seek.

Outputs: notes_now (notes fired this frame), note_log (history, for testing).
"""

import numpy as np

MAX_STEP_S = 0.5    # a forward jump bigger than this is a scrub, not playback
LOG_ROWS = 200


def onFrameStart(frame):
	comp = parent.Transport
	_syncClockLength(comp)
	now = comp.time.seconds
	prev = comp.fetch('prev_seconds', now)
	seeked = comp.fetch('seeked', False)
	comp.store('prev_seconds', now)
	if seeked:
		comp.store('seeked', False)
	notes_now = op('notes_now')
	if notes_now.numRows > 1:
		notes_now.clear(keepFirstRow=True)
	if seeked or now <= prev or now - prev > MAX_STEP_S:
		return
	for note, at in _notesSwitchedOn(op('midiin_notes'), prev, now):
		notes_now.appendRow([note, round(at, 4)])
		_log(note, now)


def _notesSwitchedOn(clip, start_s, end_s):
	"""(note, seconds) for every note whose gate rises in (start_s, end_s]."""
	rate = clip.rate
	lo = int(round(start_s * rate))
	hi = min(int(round(end_s * rate)), clip.numSamples - 1)
	if hi <= lo:
		return []
	gates = clip.numpyArray()[:, lo:hi + 1] > 0
	rising = gates[:, 1:] & ~gates[:, :-1]
	chans, samples = np.nonzero(rising)
	names = [c.name for c in clip.chans()]
	events = [(int(names[c][1:]), (lo + 1 + s) / rate) for c, s in zip(chans, samples)]
	return sorted(events, key=lambda e: (e[1], e[0]))


def _syncClockLength(comp):
	"""Keep the clock's end frame equal to the audio length."""
	tm = comp.op('local/time')
	end = 1 + int(round(comp.par.Length.eval() * tm.par.rate.eval()))
	if end > 1 and tm.par.end.eval() != end:
		tm.par.end = end
		tm.par.rangeend = end


def _log(note, clock_s):
	log = op('note_log')
	info = op('info_music')
	audio_s = float(info['sample']) / max(1.0, float(info['sample_rate']))
	log.appendRow([round(clock_s, 4), note, round(audio_s, 4), absTime.frame])
	if log.numRows > LOG_ROWS + 1:
		log.deleteRow(1)
