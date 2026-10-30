"""Mapping page: dancers connect a movement to a visual in 8 slots, kept in presets A-D.

Each slot: On, Movement (a signal), Visual (an engine target), From / To (the
visual's values at the two ends of the movement), Smoothing and Sensitivity.
The slots of the current preset are written to the assignments table, which
the engine applies after its input assignment table. Every edit is saved into
the presets table at once, so switching presets never loses work.

A MIDI note can switch presets: a row 'set mapping.preset <1-4>' in the MIDI
assignment table selects A-D at that moment of the song (Follow MIDI on).

mapping_logic holds the catalogues and the row building (unit-tested in plain
Python); this extension is the TouchDesigner side.
"""

from typing import Optional

SLOT_PARS = {'on': 'on', 'signal': 'signal', 'target': 'target', 'from': 'from', 'to': 'to',
	'smooth': 'smooth', 'sens': 'sens'}


class MappingsExt:
	"""The mapping page: slot parameters, presets and the engine rows they produce."""

	def __init__(self, ownerComp: COMP) -> None:
		self.ownerComp = ownerComp

	def onDestroyTD(self) -> None:
		pass

	def onInitTD(self) -> None:
		run('args[0].postInit()', self, delayFrames=5)

	def postInit(self) -> None:
		"""Menus and engine rows from the saved state (idempotent)."""
		self.RefreshMenus()
		self.writeAssignments()

	# ------------------------------------------------------------ public

	def RefreshMenus(self) -> None:
		"""Fill the Movement and Visual menus (in the current language) from the signal and target catalogues."""
		logic = self._logic()
		signals = logic.signalCatalogue()
		live = self._liveSignals()
		signals += [name for name in live if name not in signals]
		targets = logic.targetCatalogue(self._knownTargets())
		# The slot menus read these tables (menuSource), so the menus are not
		# stored 8 times over in every parameter.
		self._writeMenu('signal_menu', [(name, self._text('signal.' + name, name)) for name in signals])
		self._writeMenu('target_menu', [(name, self._text('target.' + name, name)) for name in targets])
		for i in range(1, logic.NUM_SLOTS + 1):
			for field, table in (('signal', 'signal_menu'), ('target', 'target_menu')):
				par = self._slotPar(i, field)
				source = "tdu.TableMenu(me.op('%s'), labelCol=1, includeFirstRow=True)" % table
				if par.menuSource != source:
					par.menuSource = source

	def LoadPreset(self, preset: Optional[str] = None) -> None:
		"""Show preset A-D (default: the Preset parameter) in the slots and send it to the engine."""
		logic = self._logic()
		preset = preset or self.ownerComp.par.Preset.eval()
		slots = self._presets()[preset]
		for i, slot in enumerate(slots, start=1):
			for field in logic.SLOT_FIELDS:
				self._slotPar(i, field).val = slot[field]
		self.writeAssignments()

	def CopyPreset(self, source: str, destination: str) -> None:
		"""Copy every slot of preset source into preset destination."""
		presets = self._presets()
		presets[destination] = [dict(s) for s in presets[source]]
		self._writePresets(presets)
		if self.ownerComp.par.Preset.eval() == destination:
			self.LoadPreset(destination)

	def ClearPreset(self, preset: str) -> None:
		"""Empty every slot of a preset."""
		presets = self._presets()
		presets[preset] = self._logic().emptySlots()
		self._writePresets(presets)
		if self.ownerComp.par.Preset.eval() == preset:
			self.LoadPreset(preset)

	# ------------------------------------------------------------ wiring (called by the COMP's own DATs)

	def onSlotChange(self, par: Par, prev) -> None:
		"""A slot parameter changed: new target -> its natural From / To; then save and send.

		Parameter Execute callbacks arrive a frame late, after LoadPreset has
		finished, so a change is judged against the stored preset: values that
		match it came from loading a preset, not from the user, and change nothing.
		"""
		slot, field = self._slotOf(par)
		if slot is None:
			return
		stored = self._presets()[self.ownerComp.par.Preset.eval()]
		# Every slot, not only this one: callbacks for several changes in one frame
		# arrive one by one, and the first one saves them all.
		for i, (current, old) in enumerate(zip(self._currentSlots(), stored), start=1):
			if current['target'] != old['target']:
				low, high = self._logic().targetRange(current['target'])
				self._slotPar(i, 'from').val = low
				self._slotPar(i, 'to').val = high
		if self._currentSlots() != stored:
			self._saveCurrent()
		self.writeAssignments()

	def onMidiPreset(self, value: float) -> None:
		"""The engine's mapping_preset changed (a MIDI 'mapping.preset' row): switch preset if following MIDI."""
		if not self.ownerComp.par.Followmidi.eval():
			return
		preset = self._logic().presetFromMidi(value)
		if preset and preset != self.ownerComp.par.Preset.eval():
			self.ownerComp.par.Preset = preset

	def writeAssignments(self) -> None:
		"""Write the current slots as engine rows into the assignments table."""
		rows = self._logic().assignmentRows(self._currentSlots(), known=self._knownTargets())
		table = self.ownerComp.op('assignments')
		if [[c.val for c in r] for r in table.rows()] != rows:
			table.clear()
			for row in rows:
				table.appendRow(row)

	# ------------------------------------------------------------ private

	def _logic(self):
		return self.ownerComp.op('mapping_logic').module

	def _slotPar(self, slot: int, field: str) -> Par:
		return self.ownerComp.par['Map%d%s' % (slot, SLOT_PARS[field])]

	def _slotOf(self, par: Par):
		name = par.name
		if not name.startswith('Map'):
			return None, None
		digits = ''.join(c for c in name[3:] if c.isdigit())
		field = name[3 + len(digits):]
		return (int(digits), field) if digits and field in SLOT_PARS else (None, None)

	def _currentSlots(self) -> list:
		logic = self._logic()
		slots = []
		for i in range(1, logic.NUM_SLOTS + 1):
			slot = {}
			for field in logic.SLOT_FIELDS:
				par = self._slotPar(i, field)
				slot[field] = par.eval() if field in ('signal', 'target') else float(par.eval())
			slots.append(slot)
		return slots

	def _writeMenu(self, name: str, entries: list) -> None:
		table = self.ownerComp.op(name)
		if [[c.val for c in r] for r in table.rows()] != [list(e) for e in entries]:
			table.clear()
			for entry in entries:
				table.appendRow(entry)

	def _presets(self) -> dict:
		table = self.ownerComp.op('presets')
		return self._logic().readPresets([[c.val for c in r] for r in table.rows()])

	def _writePresets(self, presets: dict) -> None:
		rows = self._logic().presetRows(presets)
		table = self.ownerComp.op('presets')
		table.clear()
		for row in rows:
			table.appendRow(row)

	def _saveCurrent(self) -> None:
		presets = self._presets()
		presets[self.ownerComp.par.Preset.eval()] = self._currentSlots()
		self._writePresets(presets)

	def _knownTargets(self) -> list:
		engine = getattr(op, 'Engine', None)
		logic = engine.op('show_logic') if engine else None
		if logic is None:
			return []
		layers = getattr(engine.op('engine').module, 'NUM_LAYERS', 4)
		return logic.module.knownParams(layers)

	def _liveSignals(self) -> list:
		inputs = getattr(op, 'Inputs', None)
		chop = inputs.op('signals') if inputs else None
		return [c.name for c in chop.chans()] if chop is not None else []

	def _text(self, key: str, default: str) -> str:
		lang = getattr(op, 'Lang', None)
		return lang.T(key, default) if lang is not None else default
