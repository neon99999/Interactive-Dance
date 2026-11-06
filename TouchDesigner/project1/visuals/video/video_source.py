"""Video source: the image the Video Feedback instrument uses, and its Status line.

Source menu (Source page):
- Webcam: MediaPipe's camera image while body tracking (inputs > Pose) is on,
  because MediaPipe holds the webcam then; otherwise inputs > Camera's webcam
  when that is on. With neither on there is no camera image, so the test
  pattern shows and Status says how to turn one on. The instrument never
  opens a camera itself, so it cannot fight body tracking for the webcam.
- Video File: loaded only when Load is pressed (load()), and only if the file
  exists, so a missing file can never stop the project from opening.
- Test Pattern: a moving shape, to try the effect with no camera.
"""

import os

POSE, CAMERA, FILE, TEST = 0, 1, 2, 3


def _inputs():
	return getattr(op, 'Inputs', None)


def sourceIndex(frame=0):
	"""Index for switch_source. frame is unused: passing absTime.frame re-checks every frame."""
	comp = parent.Instrument
	choice = comp.par.Source.eval()
	if choice == 'webcam':
		inputs = _inputs()
		if inputs is not None and inputs.par.Posesource.eval() == 'camera' and inputs.op('mediapipe/MediaPipe/video') is not None:
			return POSE
		if inputs is not None and inputs.par.Camerasource.eval() == 'camera':
			return CAMERA
		return TEST
	if choice == 'file':
		return FILE if op('movie_file').par.file.eval() else TEST
	return TEST


def statusText(frame=0):
	"""The Source page's Status line."""
	comp = parent.Instrument
	choice = comp.par.Source.eval()
	index = sourceIndex()
	if choice == 'webcam':
		if index == POSE:
			return 'Webcam (from body tracking)'
		if index == CAMERA:
			return 'Webcam (from inputs > Camera)'
		return 'No webcam on: showing the test pattern. Turn on inputs > Pose (Camera) or inputs > Camera.'
	if choice == 'file':
		missing = comp.fetch('load_error', '', search=False)
		if missing:
			return 'File not found: %s (showing the test pattern)' % missing
		loaded = op('movie_file').par.file.eval()
		if not loaded:
			return 'No video loaded: choose a Video File and press Load'
		return 'Video file: ' + os.path.basename(loaded)
	return 'Test pattern'


def load():
	"""Load the Video File parameter into movie_file, if the file exists."""
	comp = parent.Instrument
	path = comp.par.Videofile.eval()
	full = path if os.path.isabs(path) else os.path.join(project.folder, path)
	if path and os.path.isfile(full):
		op('movie_file').par.file = path
		comp.store('load_error', '')
	else:
		op('movie_file').par.file = ''
		comp.store('load_error', path or '(no file chosen)')
