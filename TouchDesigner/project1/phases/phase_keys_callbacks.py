"""phase_keys_callbacks: number keys switch phases (1-9 = phases 1-9, 0 = phase 10).

phase_keys only listens while the Stage picture, tiles or buttons have focus,
not the control panel, so typing a number into a setting never switches phase.
"""


def onKey(dat, key, character, alt, lAlt, rAlt, ctrl, lCtrl, rCtrl, shift, lShift, rShift, state, time):
	if state and not (alt or ctrl or shift):
		parent.Phases.ext.Phases.onKey(key)


def onShortcut(dat, shortcutName, time):
	return
