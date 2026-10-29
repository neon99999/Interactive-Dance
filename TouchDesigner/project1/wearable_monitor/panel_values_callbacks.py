"""Wearable monitor values: a fixed set of channels for the panel.

Reads serial_w1_* .. serial_w3_* (inputs/signals, through the signals Select
CHOP) and outputs w1_live ... w3_btn in the SIGNALS order below, 0 where a
signal has not arrived. glsl_panel reads them by index, so keep the order.

live is worked out here rather than taken from the receiver: the receiver
prints wN_live=1 only when a wearable connects, so a TD started later would
never see it. A wearable counts as live while its readings keep changing
(sensor noise changes them every packet) and the receiver has not said
wN_live=0.
"""

SIGNALS = ('live', 'mode', 'act', 'gx', 'gy', 'gz', 'pitch', 'roll', 'hit', 'hitdir', 'still', 'btn')
WEARABLES = (1, 2, 3)
CHANGE_SIGNALS = ('ax', 'ay', 'az', 'gx', 'gy', 'gz')
LOST_AFTER_S = 1.0  # same as the receiver's LOST_AFTER_MS

# Per-wearable bookkeeping for live. Module-level on purpose: it is runtime
# state that should not be saved with the project, and starting empty after a
# reload only means one second of NO SIGNAL.
_lastReading = {}
_changedAt = {}


def onCook(scriptOp):
	now = absTime.seconds  # read every cook: makes the op cook each frame, so live can time out
	source = scriptOp.inputs[0] if scriptOp.inputs else None
	last, changed = _lastReading, _changedAt
	scriptOp.clear()
	scriptOp.isTimeSlice = False  # one sample per channel, the current value
	scriptOp.numSamples = 1
	for w in WEARABLES:
		def read(name):
			chan = source['serial_w%d_%s' % (w, name)] if source is not None else None
			return chan.eval() if chan is not None else None
		reading = tuple(read(s) for s in CHANGE_SIGNALS)
		previous = last.get(w)
		last[w] = reading
		if previous is not None and reading != previous:  # the first reading may be stale
			changed[w] = now
		live = now - changed.get(w, -1e9) < LOST_AFTER_S and read('live') != 0
		for s in SIGNALS:
			value = float(live) if s == 'live' else (read(s) or 0.0)
			scriptOp.appendChan('w%d_%s' % (w, s))[0] = value
