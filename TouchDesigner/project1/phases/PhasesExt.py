"""Phases page: the piece in phases (started by MIDI notes of the song), each with 8 placeholder events.

The Phase menu shows one phase's 8 events in the Event parameters; every
edit is saved into the phases table at once (like the mapping presets).
Each frame (phases_frame) the extension works out the phase (Follow MIDI:
the last phase note the song played), fires triggers (MIDI notes since the
last frame, wearable hits and buttons) and writes the event_state table,
which the Phase Events instrument (visuals/events) draws.

Note for This Phase edits the shown phase's note (Phasenote1-8 keep them).
Save Show / Load Show write and read one JSON file (Show File, relative to
the folder of the .toe) with the phases, the music, the mapping presets and
the instruments' settings, so a show moves to a new version of the toolkit.

phase_logic holds the rules (unit-tested in plain Python); this extension
is the TouchDesigner side.
"""

import json
import os
from typing import Optional

SHOW_VERSION = 1

LINK_LEVEL_FIELDS = ('in', 'prop', 'from', 'to')
STATE_COLUMNS = ('event', 'alpha', 'sides', 'colour', 'x', 'y', 'size', 'rotate', 'bright', 'name')


class PhasesExt:
	"""Phase and event parameters, the phases table and the live event state."""

	def __init__(self, ownerComp: COMP) -> None:
		self.ownerComp = ownerComp
		self._runner = None
		self._last = None
		self._lastMidiPhase = None
		self._cache = {'key': None, 'phases': {}}

	def onDestroyTD(self) -> None:
		pass

	def onInitTD(self) -> None:
		run('args[0].postInit()', self, delayFrames=5)

	def postInit(self) -> None:
		"""Menus and the shown phase from the saved table (idempotent)."""
		self.RefreshMenus()
		self.LoadPhase()

	# ------------------------------------------------------------ public

	def RefreshMenus(self) -> None:
		"""Fill the Trigger and Link menus (in the current language)."""
		logic = self._logic()
		self._writeMenu('trigger_menu', [(name, self._text('phase.trigger.' + name, self._text('signal.' + name, name)))
			for name in logic.triggerSources()])
		self._writeMenu('link_menu', [(name, self._text('phase.link.' + name, self._text('signal.' + name, name)))
			for name in logic.linkSources()])
		for i in range(1, logic.NUM_EVENTS + 1):
			for field, table in [('trigger', 'trigger_menu')] + [('link%din' % k, 'link_menu')
					for k in range(1, logic.NUM_LINKS + 1)]:
				par = self._eventPar(i, field)
				source = "tdu.TableMenu(me.op('%s'), labelCol=1, includeFirstRow=True)" % table
				if par.menuSource != source:
					par.menuSource = source
			self._fitEvent(i)

	def LoadPhase(self, phase: Optional[int] = None) -> None:
		"""Show phase 1-8 (default: the Phase parameter) in the Event parameters."""
		logic = self._logic()
		phase = phase or self._phase()
		for i, event in enumerate(self._phases()[phase], start=1):
			for field in logic.EVENT_FIELDS:
				self._eventPar(i, field).val = event[field]
			self._fitEvent(i)
		note = self.ownerComp.par['Phasenote%d' % phase]
		if note is not None and self.ownerComp.par['Phasenote'] is not None:
			self.ownerComp.par.Phasenote.val = int(note.eval())

	def ClearPhase(self, phase: Optional[int] = None) -> None:
		"""Empty every event of a phase."""
		phase = phase or self._phase()
		phases = self._phases()
		phases[phase] = self._logic().emptyEvents()
		self._writePhases(phases)
		if phase == self._phase():
			self.LoadPhase(phase)

	def SaveShow(self, path: Optional[str] = None) -> str:
		"""Write the whole show to a file (default: Show File). Returns the file path.

		A show is everything a student sets that is not a visual they made: the
		phases and their notes, the song and MIDI file, the mapping presets and
		triggers, and every instrument's settings.
		"""
		path = self._showPath(path)
		try:
			os.makedirs(os.path.dirname(path), exist_ok=True)
			with open(path, 'w', encoding='utf-8') as f:
				json.dump(self._collectShow(), f, indent=1, ensure_ascii=False)
		except OSError as e:
			self._status('Not saved: %s' % e)
			raise
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
		if int(stored.eval()) != int(comp.par.Phasenote.eval()):
			stored.val = int(comp.par.Phasenote.eval())

	def onEventChange(self, par, prev) -> None:
		"""An event parameter changed: a link's new property gets its usual From / To; then save.

		Judged against the stored phase (Parameter Execute callbacks arrive after
		LoadPhase): values that match it came from loading, not from the user.
		"""
		logic = self._logic()
		phase = self._phase()
		stored = self._phases()[phase]
		for i, (now, old) in enumerate(zip(self._currentEvents(), stored), start=1):
			for k in range(1, logic.NUM_LINKS + 1):
				if now['link%dprop' % k] != old['link%dprop' % k]:
					low, high = logic.propertyRange(now['link%dprop' % k])
					self._eventPar(i, 'link%dfrom' % k).val = low
					self._eventPar(i, 'link%dto' % k).val = high
			self._fitEvent(i)
		current = self._currentEvents()
		if current != stored:
			phases = self._phases()
			phases[phase] = current
			self._writePhases(phases)

	def frame(self) -> None:
		"""Once per frame: follow the song's phase notes, fire triggers, write event_state."""
		logic = self._logic()
		comp = self.ownerComp
		if self._runner is None:
			self._runner = logic.PhaseRunner()
		engine = getattr(op, 'Engine', None)
		note_ons = engine.op('engine').module.noteOns()[0] if engine else []
		t = self._transportSeconds()
		now = absTime.seconds
		last_t, last_now = self._last if self._last else (t, now)
		self._last = (t, now)
		if comp.par.Followmidi.eval():
			notes = {p: int(comp.par['Phasenote%d' % p].eval()) for p in range(1, logic.NUM_PHASES + 1)}
			switches = logic.phaseSwitches(note_ons, notes)
			# Before the first phase note the piece is in phase 1.
			midi_phase = logic.phaseAt(switches, t) or (1 if switches else None)
			if midi_phase is not None and midi_phase != self._lastMidiPhase and midi_phase != self._phase():
				comp.par.Phase = str(midi_phase)
			self._lastMidiPhase = midi_phase
		played = logic.notesBetween(note_ons, last_t, t) if 0.0 < t - last_t < 0.5 else []
		signals = self._signals()
		mapping = getattr(op, 'Mappings', None)
		ranges = mapping.op('mapping_logic').module.signalRange if mapping else (lambda name: (0.0, 1.0))
		states = self._runner.update(self._phase(), self._storedPhases()[self._phase()], signals, played,
			now, max(0.0, now - last_now), ranges)
		self._writeState(states)

	# ------------------------------------------------------------ private

	def _logic(self):
		return self.ownerComp.op('phase_logic').module

	def _phase(self) -> int:
		try:
			return int(self.ownerComp.par.Phase.eval())
		except ValueError:
			return 1

	def _eventPar(self, event: int, field: str) -> Par:
		return self.ownerComp.par['Ev%d%s' % (event, field)]

	def _fitEvent(self, event: int) -> None:
		"""Grey out what an event does not use: Note unless MIDI, Trigger when Always, Time unless timed,
		a link's settings when it has no input. The control panel's copies follow."""
		show = self._eventPar(event, 'show').eval()
		trigger = self._eventPar(event, 'trigger').eval()
		wanted = {'note': trigger == 'midi' and show != 'always', 'trigger': show != 'always',
			'time': show == 'timed'}
		logic = self._logic()
		for k in range(1, logic.NUM_LINKS + 1):
			used = self._eventPar(event, 'link%din' % k).eval() not in ('', 'none')
			for f in ('prop', 'from', 'to'):
				wanted['link%d%s' % (k, f)] = used
			low, high = logic.propertyRange(self._eventPar(event, 'link%dprop' % k).eval())
			for f in ('from', 'to'):
				for par in self._withPanelCopies(self._eventPar(event, 'link%d%s' % (k, f))):
					if (par.normMin, par.normMax) != (low, high):
						par.normMin, par.normMax = low, high
		for field, enable in wanted.items():
			for par in self._withPanelCopies(self._eventPar(event, field)):
				if par.enable != enable:
					par.enable = enable

	def _withPanelCopies(self, par: Par) -> list:
		pars = [par]
		control = getattr(op, 'Control', None)
		if control is not None:
			pars += [p for p in control.customPars if (p.bindExpr or '').endswith(".par." + par.name)
				and "op('phases')" in (p.bindExpr or '')]
		return pars

	def _currentEvents(self) -> list:
		logic = self._logic()
		events = []
		for i in range(1, logic.NUM_EVENTS + 1):
			event = {}
			for field in logic.EVENT_FIELDS:
				par = self._eventPar(i, field)
				event[field] = str(par.eval()) if field in logic.TEXT_FIELDS else float(par.eval())
			events.append(event)
		return events

	def _rows(self) -> list:
		return [[c.val for c in r] for r in self.ownerComp.op('phases').rows()]

	def _phases(self) -> dict:
		return self._logic().readPhases(self._rows())

	def _storedPhases(self) -> dict:
		"""_phases, parsed again only when the table changed (read every frame)."""
		text = self.ownerComp.op('phases').text
		if text != self._cache['key']:
			self._cache.update(key=text, phases=self._phases())
		return self._cache['phases']

	def _writePhases(self, phases: dict) -> None:
		rows = self._logic().phaseRows(phases)
		table = self.ownerComp.op('phases')
		if self._rows() != rows:
			table.clear()
			for row in rows:
				table.appendRow(row)

	def _writeState(self, states: list) -> None:
		table = self.ownerComp.op('event_state')
		rows = [list(STATE_COLUMNS)]
		for i, s in enumerate(states, start=1):
			rows.append([str(i)] + ['%.4g' % s[c] for c in STATE_COLUMNS[1:-1]] + [s['name']])
		if table.numRows != len(rows) or table.numCols != len(STATE_COLUMNS):
			table.clear()
			for row in rows:
				table.appendRow(row)
			return
		for r, row in enumerate(rows):
			for c, text in enumerate(row):
				if table[r, c].val != text:
					table[r, c] = text

	def _writeMenu(self, name: str, entries: list) -> None:
		table = self.ownerComp.op(name)
		if [[c.val for c in r] for r in table.rows()] != [list(e) for e in entries]:
			table.clear()
			for entry in entries:
				table.appendRow(entry)

	def _signals(self) -> dict:
		inputs = getattr(op, 'Inputs', None)
		chop = inputs.op('signals') if inputs else None
		return {c.name: float(c.eval()) for c in chop.chans()} if chop is not None else {}

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

	def _status(self, text: str) -> None:
		par = self.ownerComp.par['Showstatus']
		if par is not None:
			par.val = text

	def _collectShow(self) -> dict:
		comp = self.ownerComp
		show = {'version': SHOW_VERSION, 'phases': self._rows(),
			'phase_notes': [int(comp.par['Phasenote%d' % i].eval()) for i in range(1, self._logic().NUM_PHASES + 1)],
			'follow_midi': int(comp.par.Followmidi.eval())}
		transport = getattr(op, 'Transport', None)
		if transport is not None:
			show['music'] = {name: str(transport.par[name].eval()) for name in ('Audiofile', 'Midifile')}
		mappings = getattr(op, 'Mappings', None)
		if mappings is not None:
			show['mappings'] = {name: [[c.val for c in r] for r in mappings.op(name).rows()]
				for name in ('presets', 'trigger_presets')}
			show['mapping_pars'] = {p.name: self._plain(p) for p in mappings.customPars
				if p.name in ('Preset', 'Followmidi') or p.name.startswith('Presetnote')}
		visuals = getattr(op, 'Visuals', None)
		show['instruments'] = {}
		for inst in (visuals.children if visuals is not None else []):
			page = next((pg for pg in inst.customPages if pg.name == 'Instrument'), None) if inst.isCOMP else None
			if page is not None:
				show['instruments'][inst.name] = {p.name: self._plain(p) for p in page.pars
					if not p.isPulse and not p.isMomentary and p.style != 'Header' and p.mode == ParMode.CONSTANT}
		return show

	def _applyShow(self, show: dict) -> int:
		"""Set everything in a show; returns how many settings did not fit this version."""
		comp = self.ownerComp
		logic = self._logic()
		skipped = 0
		if show.get('phases'):
			self._writePhases(logic.readPhases(show['phases']))
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
					for row in rows:
						table.appendRow(row)
			for name, value in show.get('mapping_pars', {}).items():
				skipped += not self._setPar(mappings, name, value)
			mappings.LoadPreset()
		visuals = getattr(op, 'Visuals', None)
		for inst_name, values in show.get('instruments', {}).items():
			inst = visuals.op(inst_name) if visuals is not None else None
			for name, value in values.items():
				skipped += not self._setPar(inst, name, value)
		self.LoadPhase()
		return skipped

	def _setPar(self, owner, name: str, value) -> bool:
		par = owner.par[name] if owner is not None else None
		if par is None or par.mode != ParMode.CONSTANT:
			return False
		if par.isMenu and value not in par.menuNames:
			return False
		par.val = value
		return True

	def _plain(self, par: Par):
		value = par.eval()
		if par.isMenu or par.isString:
			return str(value)
		return float(value) if par.style == 'Float' else int(value)

	def _text(self, key: str, default: str) -> str:
		lang = getattr(op, 'Lang', None)
		return lang.T(key, default) if lang is not None else default
