"""Camera instrument: the webcam picture (or a test pattern), with an optional echo.

Source menu (Source page):
- Webcam: MediaPipe's camera image with inputs > Webcam > Use on Body
  Tracking, because MediaPipe holds the webcam then; camera_in's picture on
  Movement Only. With neither on there is no camera image, so the test
  pattern shows and Status says how to turn one on. The instrument never
  opens a camera itself, so it cannot fight body tracking for the webcam.
- Test Pattern: a moving shape, to try it with no camera.

Echo menu (Instrument page): what leaves trails.
- Off: the plain camera picture.
- Dancer: only the dancer repeats. Uses MediaPipe's body mask, so it needs
  body tracking on (inputs > Webcam > Use: Body Tracking, Body Mask on).
- Movement: only what moves repeats (this frame compared with the last one).
- Auto: Dancer when it is available, otherwise Movement.
Whole-picture echo is the master effect Trails (visuals/master_fx).
"""

import os

POSE, CAMERA, TEST = 0, 1, 2
# Echo results: index for switch_mask (DANCER, MOVEMENT); OFF shows the plain picture.
DANCER, MOVEMENT, OFF = 0, 1, 2
ECHO_MENU = ('off', 'auto', 'dancer', 'movement')


def _inputs():
	return getattr(op, 'Inputs', None)


def sourceIndex(frame=0):
	"""Index for switch_source. frame is unused: passing absTime.frame re-checks every frame."""
	comp = parent.Instrument
	if comp.par.Source.eval() == 'webcam':
		inputs = _inputs()
		if inputs is not None and inputs.par.Posesource.eval() == 'camera' and inputs.op('mediapipe/MediaPipe/video') is not None:
			return POSE
		if inputs is not None and inputs.par.Camerasource.eval() == 'camera':
			return CAMERA
	return TEST


def hasBodyMask():
	"""True when MediaPipe's body mask matches the picture in use."""
	inputs = _inputs()
	return (sourceIndex() == POSE and inputs is not None
		and bool(inputs.par.Posemask.eval())
		and inputs.op('mediapipe/MediaPipe/segmentation') is not None)


def echoMode(frame=0):
	"""DANCER, MOVEMENT or OFF for the Echo menu value now in use (mapped or manual)."""
	channel = op('live')['echo']
	index = int(round(channel.eval())) if channel is not None else 1
	choice = ECHO_MENU[max(0, min(index, len(ECHO_MENU) - 1))]
	if choice == 'off':
		return OFF
	if choice in ('auto', 'dancer') and hasBodyMask():
		return DANCER
	return MOVEMENT


def mix(frame=0):
	"""cross_mix: the Mix setting, or 0 (plain picture) when Echo is Off."""
	return 0.0 if echoMode() == OFF else float(op('live')['mix'])


def statusText(frame=0):
	"""The Source page's Status line: the picture in use, then what echoes."""
	echo = {DANCER: 'Echo: dancer', MOVEMENT: 'Echo: movement', OFF: 'Echo: off'}[echoMode()]
	return _sourceText().rstrip('.') + '. ' + echo


def _sourceText():
	index = sourceIndex()
	if parent.Instrument.par.Source.eval() == 'webcam':
		if index == POSE:
			return 'Webcam (from body tracking)'
		if index == CAMERA:
			return 'Webcam (movement only, from inputs > Webcam)'
		return 'No webcam on: showing the test pattern. Set inputs > Webcam > Use to Body Tracking or Movement Only.'
	return 'Test pattern'
