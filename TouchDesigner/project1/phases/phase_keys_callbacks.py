"""phase_keys_callbacks: number keys switch phases (1-9 = phases 1-9, 0 = phase 10).

phase_keys listens everywhere in TouchDesigner (Panels empty), the control
panel too. So that typing a value (Note 60, Position 12.5) does not switch
the phase, a number key acts only when no other key comes WAIT_S before or
after it (typing a value has a second key close by: a digit, Enter, Tab,
Backspace, '.'). Keys with Alt, Ctrl, Shift or Cmd are ignored.
"""

WAIT_S = 0.4
_state = {'key': None, 'serial': 0, 'last': -100.0}


def onKey(dat, key, character, alt, lAlt, rAlt, ctrl, lCtrl, rCtrl, shift, lShift, rShift, state, time, cmd=False, lCmd=False, rCmd=False):
	if not state:
		return
	now = absTime.seconds
	quiet = now - _state['last'] >= WAIT_S
	_state['last'] = now
	_state['serial'] += 1
	_state['key'] = None  # any key cancels a waiting number
	if len(key) == 1 and key in '0123456789' and quiet and not (alt or ctrl or shift or cmd):
		_state['key'] = key
		run('args[0](args[1])', _fire, _state['serial'], delayMilliSeconds=int(WAIT_S * 1000))


def _fire(serial):
	key = _state['key']
	if key is not None and serial == _state['serial']:
		_state['key'] = None
		op.Phases.ext.Phases.onKey(key)


def onShortcut(dat, shortcutName, time):
	return
