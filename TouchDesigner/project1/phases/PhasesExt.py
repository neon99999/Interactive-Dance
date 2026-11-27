"""Phases page: the piece in up to 10 phases; each phase keeps its own instrument and mapping settings.

A phase is one part of the song. While a phase is shown, every change to an
instrument (its Instrument, Source or Layer page) is kept in that phase's
snapshot (the phase_settings table), and the mappings keep one set per
phase (the mappings component's Preset follows the phase). Changing phase
puts the new phase's settings back; a phase that has none yet starts as a
copy of the settings on screen.

The phase changes from the Phase menu, the number keys (1-9 = phases 1-9,
0 = phase 10, see phase_keys) or the song: with Follow MIDI on, the last
phase note (Note for This Phase) the song played selects the phase.

Autosave: a few seconds after a change, the whole show is written to
shows/autosave.json. When the project opens and that file is newer than
the .toe, it is loaded, so work since the last save of the .toe is kept.
Save Show / Load Show write and read a show file by name (Show File).

phase_logic holds the rules (unit-tested in plain Python); this extension
is the TouchDesigner side.
"""

import json
import os
from typing import Optional

SHOW_VERSION = 2
AUTOSAVE = 'shows/autosave.json'
AUTOSAVE_DELAY_S = 3.0
CAPTURE_EVERY = 10          # frames between looks for changed settings
SETTLE_FRAMES = 6           # after a phase change, wait for preset callbacks before capturing
SNAPSHOT_PAGES = ('Instrument', 'Source', 'Layer')
SNAPSHOT_SKIP = ('Status',)
SNAPSHOT_STYLES = ('Float', 'Int', 'Toggle', 'Menu', 'StrMenu', 'Str', 'File', 'Folder', 'RGBA', 'RGB')


class PhasesExt:
	"""Phase parameters, per-phase settings snapshots, autosave and the show file."""

	def __init__(self, ownerComp: COMP) -> None:
		self.ownerComp = ownerComp
		self._lastMidiPhase = None
		self._shown = None          # the phase whose settings are on screen
		self._settleUntil = 0
		self._dirtySince = None

	def onDestroyTD(self) -> None:
		pass

	def onInitTD(self) -> None:
		run('args[0].postInit()', self, delayFrames=5)

	def postInit(self) -> None:
		"""Restore a newer autosave, then show the current phase (idempotent)."""
		if self._shown is None and self._autosaveIsNewer():
			try:
				self.LoadShow(AUTOSAVE)
				self._status('Restored autosave')
			except (OSError, ValueError):
				pass
		self._shown = self._phase()
		self.LoadPhase()

	# ------------------------------------------------------------ public

	def LoadPhase(self, phase: Optional[int] = None) -> None:
		"""Show phase 1-10 (default: the Phase parameter): keep the old phase's settings, put the new phase's back."""
		phase = phase or self._phase()
		comp = self.ownerComp
		if self._shown is not None and self._shown != phase:
			self.capture(self._shown)
		snaps = self._snapshots()
		if phase in snaps:
			self._apply(snaps[phase])
		else:
			snaps[phase] = self._collect()
			self._writeSnapshots(snaps)
		self._shown = phase
		self._settleUntil = absTime.frame + SETTLE_FRAMES
		mappings = getattr(op, 'Mappings', None)
		if mappings is not None and mappings.par.Preset.eval() != str(phase):
			mappings.par.Preset = str(phase)
		note = comp.par['Phasenote%d' % phase]
		if note is not None and int(comp.par.Phasenote.eval()) != int(note.eval()):
			comp.par.Phasenote.val = int(note.eval())

	def SelectPhase(self, phase: int) -> None:
		"""Switch to phase 1-10 now (number keys, scripts)."""
		if 1 <= phase <= self._logic().NUM_PHASES and phase != self._phase():
			self.ownerComp.par.Phase = str(phase)

	def SaveShow(self, path: Optional[str] = None, quiet: bool = False) -> str:
		"""Write the whole show to a file (default: Show File). Returns the file path.

		A show is everything a student sets: the phases with their settings and
		notes, the song and MIDI file, the mappings and triggers of every phase,
		and the instruments' settings.
		"""
		if self._shown is not None:
			self.capture(self._shown)
		path = self._showPath(path)
		try:
			os.makedirs(os.path.dirname(path), exist_ok=True)
			tmp = path + '.tmp'
			with open(tmp, 'w', encoding='utf-8') as f:
				json.dump(self._collectShow(), f, indent=1, ensure_ascii=False)
			os.replace(tmp, path)
		except OSError as e:
			self._status('Not saved: %s' % e)
			raise
		if not quiet:
			self._status('Saved %s' % os.path.basename(path))
		return path

	def LoadShow(self, path: Optional[str] = None) -> str:
		"""Read a show file (default: Show File) and set everything in it. Returns the file path."""
		path = self._showPath(path)
		try:
			with open(path, encoding='utf-8') as f:
				show = json.load(f)
		except (OSError, ValueError) as e:
			self._status('Not loaded: %s' % e)
			raise
		skipped = self._applyShow(show)
		self._status('Loaded %s%s' % (os.path.basename(path), ' (%d settings skipped)' % skipped if skipped else ''))
		return path

	# ------------------------------------------------------------ wiring (called by the COMP's own DATs)

	def onPhaseNoteChange(self) -> None:
		"""Note for This Phase changed: keep it as the shown phase's note."""
		comp = self.ownerComp
		stored = comp.par['Phasenote%d' % self._phase()]
		if stored is not None and int(stored.eval()) != int(comp.par.Phasenote.eval()):
			stored.val = int(comp.par.Phasenote.eval())
			self.markDirty()

	def onKey(self, key: str) -> None:
		"""A number key was pressed: 1-9 select phases 1-9, 0 selects phase 10."""
		phase = self._logic().keyPhase(key)
		if phase is not None:
			self.SelectPhase(phase)

	def capture(self, phase: Optional[int] = None) -> bool:
		"""Keep the settings on screen as phase's snapshot. Returns True when something changed."""
		phase = phase or self._shown or self._phase()
		snaps = self._snapshots()
		current = self._collect()
		if not self._logic().changedSettings(current, snaps.get(phase, {})) and phase in snaps:
			return False
		snaps[phase] = current
		self._writeSnapshots(snaps)
		self.markDirty()
		return True

	def frame(self) -> None:
		"""Once per frame: follow the song's phase notes; now and then keep changed settings and autosave."""
		logic = self._logic()
		comp = self.ownerComp
		if comp.par.Followmidi.eval():
			engine = getattr(op, 'Engine', None)
			note_ons = engine.op('engine').module.noteOns()[0] if engine else []
			notes = {p: int(comp.par['Phasenote%d' % p].eval()) for p in range(1, logic.NUM_PHASES + 1)}
			switches = logic.phaseSwitches(note_ons, notes)
			# Before the first phase note the piece is in phase 1.
			midi_phase = logic.phaseAt(switches, self._transportSeconds()) or (1 if switches else None)
			if midi_phase is not None and midi_phase != self._lastMidiPhase and midi_phase != self._phase():
				comp.par.Phase = str(midi_phase)
			self._lastMidiPhase = midi_phase
		frame = absTime.frame
		if self._shown is not None and frame >= self._settleUntil and frame % CAPTURE_EVERY == 0:
			self.capture(self._shown)
		if self._dirtySince is not None and absTime.seconds - self._dirtySince > AUTOSAVE_DELAY_S:
			self._dirtySince = None
			try:
				self.SaveShow(AUTOSAVE, quiet=True)
			except OSError:
				pass

	def isApplying(self) -> bool:
		"""True for a few frames after a phase change put settings back (preset callbacks then do nothing)."""
		return absTime.frame < self._settleUntil

	# ------------------------------------------------------------ private

	def _logic(self):
		return self.ownerComp.op('phase_logic').module

	def _phase(self) -> int:
		try:
			return int(self.ownerComp.par.Phase.eval())
		except ValueError:
			return 1

	def markDirty(self) -> None:
		if self._dirtySince is None:
			self._dirtySince = absTime.seconds

	def _instrumentComps(self) -> list:
		"""The visuals COMPs whose settings a phase keeps."""
		visuals = getattr(op, 'Visuals', None)
		if visuals is None:
			return []
		return [c for c in visuals.children if c.isCOMP and any(pg.name in SNAPSHOT_PAGES for pg in c.customPages)]

	def _snapshotPars(self, comp: COMP) -> list:
		pars = []
		for page in comp.customPages:
			if page.name in SNAPSHOT_PAGES:
				pars += [p for p in page.pars if p.style in SNAPSHOT_STYLES and p.name not in SNAPSHOT_SKIP
					and p.mode == ParMode.CONSTANT and not p.readOnly]
		return pars

	def _collect(self) -> dict:
		"""{comp name: {par: value}} of the settings on screen."""
		return {comp.name: {p.name: self._plain(p) for p in self._snapshotPars(comp)} for comp in self._instrumentComps()}

	def _apply(self, snapshot: dict) -> None:
		"""Put a snapshot's settings back. Preset menus first, so their callbacks cannot undo the rest."""
		visuals = getattr(op, 'Visuals', None)
		if visuals is None:
			return
		self._settleUntil = absTime.frame + SETTLE_FRAMES
		for comp_name, values in snapshot.items():
			comp = visuals.op(comp_name)
			if comp is None:
				continue
			names = sorted(values, key=lambda n: n != 'Preset')
			for name in names:
				self._setPar(comp, name, values[name])
			# A setting the phase does not know (added after it was saved) goes to its default.
			for par in self._snapshotPars(comp):
				if par.name not in values:
					self._setPar(comp, par.name, par.default)

	def _snapshots(self) -> dict:
		table = self.ownerComp.op('phase_settings')
		return self._logic().readSnapshots([[c.val for c in r] for r in table.rows()])

	def _writeSnapshots(self, snaps: dict) -> None:
		rows = self._logic().snapshotRows(snaps)
		table = self.ownerComp.op('phase_settings')
		# One appendRows, not one appendRow per row: the table is synced to a file,
		# and each appendRow wrote the whole file again (578 rows took 2.3 s and froze the show).
		table.clear()
		table.appendRows([[str(c) for c in row] for row in rows])

	def _transportSeconds(self) -> float:
		transport = getattr(op, 'Transport', None)
		return float(transport.time.seconds) if transport else 0.0

	def _showPath(self, path: Optional[str]) -> str:
		"""An absolute path: a relative one is taken from the folder of the .toe."""
		par = self.ownerComp.par['Showfile']
		path = path or (str(par.eval()) if par is not None else '') or 'shows/my_show.json'
		if not path.lower().endswith('.json'):
			path += '.json'
		return os.path.normpath(path if os.path.isabs(path) else os.path.join(project.folder, path))

	def _autosaveIsNewer(self) -> bool:
		path = self._showPath(AUTOSAVE)
		toe = os.path.join(project.folder, project.name)
		try:
			return os.path.getmtime(path) > os.path.getmtime(toe)
		except OSError:
			return False

	def _status(self, text: str) -> None:
		par = self.ownerComp.par['Showstatus']
		if par is not None:
			par.val = text

	def _collectShow(self) -> dict:
		comp = self.ownerComp
		logic = self._logic()
		show = {'version': SHOW_VERSION, 'phase': self._phase(),
			'phase_settings': [[c.val for c in r] for r in comp.op('phase_settings').rows()],
			'phase_notes': [int(comp.par['Phasenote%d' % i].eval()) for i in range(1, logic.NUM_PHASES + 1)],
			'follow_midi': int(comp.par.Followmidi.eval())}
		transport = getattr(op, 'Transport', None)
		if transport is not None:
			show['music'] = {name: str(transport.par[name].eval()) for name in ('Audiofile', 'Midifile')}
		mappings = getattr(op, 'Mappings', None)
		if mappings is not None:
			show['mappings'] = {name: [[c.val for c in r] for r in mappings.op(name).rows()]
				for name in ('presets', 'trigger_presets')}
		show['instruments'] = self._collect()
		return show

	def _applyShow(self, show: dict) -> int:
		"""Set everything in a show; returns how many settings did not fit this version."""
		comp = self.ownerComp
		logic = self._logic()
		skipped = 0
		rows = show.get('phase_settings')
		snaps = logic.readSnapshots(rows) if rows else {}
		self._writeSnapshots(snaps)
		for i, note in enumerate(show.get('phase_notes', [])[:logic.NUM_PHASES], start=1):
			comp.par['Phasenote%d' % i] = int(note)
		if 'follow_midi' in show:
			comp.par.Followmidi = int(show['follow_midi'])
		transport = getattr(op, 'Transport', None)
		for name, value in show.get('music', {}).items():
			skipped += not self._setPar(transport, name, value)
		mappings = getattr(op, 'Mappings', None)
		if mappings is not None:
			for name, rows in show.get('mappings', {}).items():
				table = mappings.op(name) if name in ('presets', 'trigger_presets') else None
				if table is not None:
					table.clear()
					table.appendRows([[str(c) for c in row] for row in rows])
		visuals = getattr(op, 'Visuals', None)
		for inst_name, values in show.get('instruments', {}).items():
			inst = visuals.op(inst_name) if visuals is not None else None
			for name, value in values.items():
				if name in ('Blend', 'Order', 'Mix'):
					continue
				skipped += not self._setPar(inst, name, value)
		phase = int(show.get('phase', self._phase()))
		self._shown = None
		if 1 <= phase <= logic.NUM_PHASES and phase != self._phase():
			comp.par.Phase = str(phase)
		if mappings is not None:
			mappings.par.Preset = str(phase if 1 <= phase <= logic.NUM_PHASES else self._phase())
			mappings.LoadPreset()
		self.LoadPhase(phase if 1 <= phase <= logic.NUM_PHASES else None)
		self._dirtySince = None
		return skipped

	def _setPar(self, owner, name: str, value) -> bool:
		par = owner.par[name] if owner is not None else None
		if par is None or par.mode != ParMode.CONSTANT or par.readOnly:
			return False
		if par.isMenu and par.style == 'Menu' and value not in par.menuNames:
			return False
		try:
			if par.isMenu or par.isString:
				if str(par.eval()) != str(value):
					par.val = str(value)
			elif par.style == 'Float' or par.style in ('RGB', 'RGBA'):
				if abs(float(par.eval()) - float(value)) > 1e-9:
					par.val = float(value)
			elif int(par.eval()) != int(float(value)):
				par.val = int(float(value))
		except (TypeError, ValueError):
			return False
		return True

	def _plain(self, par: Par):
		value = par.eval()
		if par.isMenu or par.isString:
			return str(value)
		return float(value) if par.style in ('Float', 'RGB', 'RGBA') else int(value)

	def _text(self, key: str, default: str) -> str:
		lang = getattr(op, 'Lang', None)
		return lang.T(key, default) if lang is not None else default
