"""Phases page: the piece in phases (started by MIDI notes of the song), each with 8 placeholder events.

The Phase menu shows one phase's 8 events in the Event parameters; every
edit is saved into the phases table at once (like the mapping presets).
Each frame (phases_frame) the extension works out the phase (Follow MIDI:
the last phase note the song played), fires triggers (MIDI notes since the
last frame, wearable hits and buttons) and writes the event_state table,
which the Phase Events instrument (visuals/events) draws.

phase_logic holds the rules (unit-tested in plain Python); this extension
is the TouchDesigner side.
"""

from typing import Optional

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

	def ClearPhase(self, phase: Optional[int] = None) -> None:
		"""Empty every event of a phase."""
		phase = phase or self._phase()
		phases = self._phases()
		phases[phase] = self._logic().emptyEvents()
		self._writePhases(phases)
		if phase == self._phase():
			self.LoadPhase(phase)

	def CopyPhase(self, source: int, destination: int) -> None:
		"""Copy every event of phase source into phase destination."""
		phases = self._phases()
		phases[destination] = [dict(e) for e in phases[source]]
		self._writePhases(phases)
		if destination == self._phase():
			self.LoadPhase(destination)

	# ------------------------------------------------------------ wiring (called by the COMP's own DATs)

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

	def _text(self, key: str, default: str) -> str:
		lang = getattr(op, 'Lang', None)
		return lang.T(key, default) if lang is not None else default
