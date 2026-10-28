"""MIDI monitor: show each Note On in the MIDI file for Hold Time seconds as it plays.

Like the engine, it is driven by the playback position, so pause, seek and
Reset show exactly the notes due at that point. The big number is the note
number used in the MIDI assignment table; the line below adds the note names
(60 = C4) and the playback time.
"""

FLASH_S = 0.15


def onFrameStart(frame):
	engine = getattr(op, 'Engine', None)
	transport = getattr(op, 'Transport', None)
	if engine is None or transport is None:
		return
	sl = engine.op('show_logic').module
	notes, _ = engine.op('engine').module.noteOns()
	t = float(transport.time.seconds)
	hold = max(0.1, float(parent.Monitor.par.Holdtime.eval()))
	recent = sl.recentNotes(notes, t, hold)
	if recent:
		label = ' '.join(sl.noteName(n) for n, _ in recent)
	else:
		label = '' if notes else 'no notes in the MIDI file'
	_setText(op('text_notes'), '  '.join(str(n) for n, _ in recent))
	_setText(op('text_info'), ('%s     %.2f s' % (label, t)).strip())
	newest = recent[-1][1] if recent else hold
	_setPar(op('text_notes').par.fontalpha, round(1.0 - 0.7 * newest / hold, 3))
	glow = round(0.08 + 0.35 * max(0.0, 1.0 - newest / FLASH_S), 3)
	info = op('text_info')
	for par in (info.par.bgcolorr, info.par.bgcolorg, info.par.bgcolorb):
		_setPar(par, glow)


def _setText(text_top, text):
	_setPar(text_top.par.text, text)


def _setPar(par, value):
	"""Set only on change, so the text TOPs do not recook every frame."""
	if par.eval() != value:
		par.val = value
