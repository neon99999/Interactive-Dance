"""Stage: the one screen people use, in its own window (op.Stage.Open()).

Left: a big view (the output, or whichever tile was clicked) over eight live
tiles: Output, the four instruments and three monitors (body tracking,
wearables, MIDI notes). Right: the control panel's five tabs (a Parameter
COMP showing control, so every setting still lives where it did). A hidden
instrument's tile stays dark (so it does not cook) until it is clicked. Bottom:
Play, Reset, the playback time, three test buttons, the output window and
the language.

The stage holds no show settings of its own. Play is bound to transport,
each tile's On to its instrument's Visible. The three tests change a few
settings and put them back when switched off:
  Test Track    transport plays media/test (the demo cues at 5, 10, 15, 20 s)
  Test Pattern  the Camera instrument shows the test pattern
  Test Dancer   inputs Use: Test, a made-up dancer for the pose signals
The settings they replace are kept in storage ('testPrevious').
"""

from typing import Optional

INSTRUMENTS = ('noise', 'video', 'shapes', 'particles')
MONITORS = {'pose': 'pose_monitor', 'wearable': 'wearable_monitor', 'midi': 'midi_monitor'}
TILES = ('output', 'noise', 'video', 'shapes', 'particles', 'pose', 'wearable', 'midi')
TEST_AUDIO = '../media/test/sync_test.wav'
TEST_MIDI = '../media/test/sync_test.mid'


class StageExt:
	"""The stage window: views, tiles and test switches."""

	def __init__(self, ownerComp: COMP) -> None:
		self.ownerComp = ownerComp

	def onDestroyTD(self) -> None:
		pass

	def onInitTD(self) -> None:
		pass

	# Public: called by people (annotation, Textport).

	def Open(self) -> None:
		"""Open the stage window."""
		self.ownerComp.op('stage_window').par.winopen.pulse()

	def Close(self) -> None:
		"""Close the stage window."""
		self.ownerComp.op('stage_window').par.winclose.pulse()

	# Wiring: called by the stage's own expressions and callback DATs.

	def tileTop(self, name: str, tile: bool = False) -> Optional[TOP]:
		"""The image a tile (tile=True) or the big view shows.

		A hidden instrument's tile stays dark unless it is in the big view:
		showing it would make it cook every frame and cost frame rate."""
		if tile and name in INSTRUMENTS and not self.isOn(name) and self.ownerComp.par.Mainview.eval() != name:
			return None
		if name == 'output':
			return op.Visuals.op('null_out')
		if name in INSTRUMENTS:
			return op.Visuals.op(name + '/out1')
		if name in MONITORS:
			return self.ownerComp.parent().op(MONITORS[name] + '/null_out')
		return None

	def label(self, name: str) -> str:
		return op.Lang.T('stage.' + name, name)

	def isOn(self, name: str) -> bool:
		"""Whether an instrument is in the output now (MIDI and mappings included)."""
		live = op.Engine.op('live')
		channel = live[name + '_visible'] if live is not None else None
		return channel is not None and channel.eval() >= 0.5

	def tileLabel(self, name: str) -> str:
		if name in INSTRUMENTS and not self.isOn(name):
			return '%s  (%s)' % (self.label(name), self.label('hidden'))
		return self.label(name)

	def viewLabel(self) -> str:
		name = self.ownerComp.par.Mainview.eval()
		text = op.Lang.T('stage.showing', 'Showing: {0}').replace('{0}', self.tileLabel(name))
		return text if name == 'output' else text + '   (' + self.label('back') + ')'

	def timeText(self) -> str:
		t = op.Transport
		position, length = t.par.Position.eval(), t.par.Length.eval()
		return '%d:%02d / %d:%02d' % (position // 60, position % 60, length // 60, length % 60)

	def onTileClick(self, tile: COMP) -> None:
		name = tile.name[len('tile_'):]
		if name in TILES:
			self.ownerComp.par.Mainview = name

	def onButton(self, button: COMP) -> None:
		"""A momentary button in the bottom bar was pressed."""
		name = button.name
		if name == 'btn_reset':
			op.Transport.par.Reset.pulse()
		elif name == 'btn_openoutput':
			op.Visuals.par.Openwindow.pulse()
		elif name == 'btn_closeoutput':
			op.Visuals.par.Closewindow.pulse()
		elif name == 'btn_language':
			lang = op.Lang.par.Language
			lang.val = 'es' if lang.eval() == 'en' else 'en'

	def onParValueChange(self, par: Par, prev) -> None:
		handler = getattr(self, '_on%sValueChange' % par.name, None)
		if callable(handler):
			handler(par, prev)

	# Private.

	def _previous(self) -> dict:
		return dict(self.ownerComp.fetch('testPrevious', {}, search=False))

	def _keep(self, key: str, values: dict) -> None:
		saved = self._previous()
		saved[key] = values
		self.ownerComp.store('testPrevious', saved)

	def _restore(self, key: str) -> None:
		saved = self._previous()
		for path, value in saved.pop(key, {}).items():
			comp_path, par_name = path.rsplit(':', 1)
			target = op(comp_path)
			if target is not None and hasattr(target.par, par_name):
				getattr(target.par, par_name).val = value
		self.ownerComp.store('testPrevious', saved)

	def _set(self, key: str, values: dict) -> None:
		"""Remember the current values of {(comp, par name): new value}, then set them."""
		self._keep(key, {'%s:%s' % (comp.path, name): getattr(comp.par, name).eval() for (comp, name) in values})
		for (comp, name), value in values.items():
			getattr(comp.par, name).val = value

	def _onTesttrackValueChange(self, par: Par, prev) -> None:
		t = op.Transport
		t.par.Play = False
		if par.eval():
			self._set('track', {(t, 'Audiofile'): TEST_AUDIO, (t, 'Midifile'): TEST_MIDI})
		else:
			self._restore('track')
		t.par.Reset.pulse()

	def _onTestpatternValueChange(self, par: Par, prev) -> None:
		video = op.Visuals.op('video')
		if par.eval():
			self._set('pattern', {(video, 'Source'): 'test', (video, 'Visible'): True})
		else:
			self._restore('pattern')

	def _onTestdancerValueChange(self, par: Par, prev) -> None:
		if par.eval():
			self._set('dancer', {(op.Inputs, 'Webcamuse'): 'test'})
		else:
			self._restore('dancer')
