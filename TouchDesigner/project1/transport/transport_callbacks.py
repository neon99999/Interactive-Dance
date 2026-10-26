"""Transport controls: Play, Reset and Seek drive the transport's local clock.

The local Time COMP (local/time) is the single playback position for audio
and MIDI. Reset and Seek mark the jump so note_events fires nothing for it.
"""


def onValueChange(par, prev):
	handler = globals().get('_on%sValueChange' % par.name)
	if handler:
		handler(par)


def onPulse(par):
	handler = globals().get('_on%sPulse' % par.name)
	if handler:
		handler(par)


def _onPlayValueChange(par):
	par.owner.op('local/time').par.play = int(par.eval())


def _onResetPulse(par):
	_jumpTo(par.owner, 0.0)


def _onSeekPulse(par):
	_jumpTo(par.owner, par.owner.par.Seekto.eval())


def _jumpTo(comp, seconds):
	"""Move the shared clock to `seconds`, clamped to the audio length."""
	seconds = min(max(0.0, float(seconds)), float(comp.par.Length.eval()))
	comp.store('seeked', True)
	comp.time.frame = comp.time.start + seconds * comp.time.rate
