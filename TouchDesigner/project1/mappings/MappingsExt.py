"""Mapping page: dancers connect a movement to a visual in 8 slots, kept per phase (presets 1-10).

Each slot is chosen in four short menus: Source (Wearable 1, Body, ...) and
Input (Tilt sideways, ...) make the movement signal; Instrument (Particles,
...) and Setting (Size, ...) make the visual target. The slot stores the
signal and target names (hidden Movement / Visual parameters), so presets
and show files keep their format; the menus are worked out from them.

The preset is the phase: the phases component sets Preset to the phase
number, so every phase has its own mappings and triggers.

Each slot: On, Movement (a signal), Visual (an engine target), From / To (the
visual's values at the two ends of the movement), Smoothing and Sensitivity.
The slots of the current preset are written to the assignments table, which
the engine applies after its input assignment table. Every edit is saved into
the presets table at once, so switching presets never loses work.

Each preset also holds 8 triggers (Triggers page): When (a MIDI note of the
song, or a wearable hit or button), Note, Does (pulse, spin, sides, jump,
flash) and Amount, acted out by the Trigger Shape instrument. They are kept
in trigger_presets and read by the engine (show_logic, triggers).

A MIDI note can switch presets: Note for Preset A-D on the Mappings page, or
a row 'set mapping.preset <1-4>' in the MIDI assignment table, selects A-D at
that moment of the song (Follow MIDI on).

mapping_logic holds the catalogues and the row building (unit-tested in plain
Python); this extension is the TouchDesigner side.
"""

import re
from typing import Optional

SLOT_PARS = {'on': 'on', 'signal': 'signal', 'target': 'target', 'from': 'from', 'to': 'to',
	'smooth': 'smooth', 'sens': 'sens', 'source': 'source', 'input': 'input', 'instrument': 'instrument',
	'setting': 'setting'}
MENU_FIELDS = ('source', 'input', 'instrument', 'setting')
TRIGGER_MENU_FIELDS = ('source', 'input')
NONE = 'none'


class _Menu:
	"""A menu for a parameter's menuSource: names and labels."""

	def __init__(self, names: list, labels: list) -> None:
		self.menuNames = names
		self.menuLabels = labels


class MappingsExt:
	"""The mapping page: slot parameters, presets and the engine rows they produce."""

	def __init__(self, ownerComp: COMP) -> None:
		self.ownerComp = ownerComp
		self._syncing = False

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
		self._writeMenu('trigger_when_menu', [(name, self._text('trigger.when.' + name, self._text('signal.' + name, name)))
			for name in logic.triggerSources()])
		# Every action a trigger row can hold: the Trigger Shape's own, then the
		# connections' bursts and counters on any instrument (written by the connections).
		actions = [(name, self._text('trigger.does.' + name, name)) for name in logic.TRIGGER_ACTIONS]
		for instrument in logic.instrumentsOf(targets):
			settings = logic.settingsOf(instrument, targets)
			for does in logic.doesOptions(instrument, ('moment',), settings):
				if does.startswith(('burst:', 'count:')):
					actions.append((logic.triggerAction(instrument, does), self._text('instrument.' + instrument, instrument)
						+ ': ' + self._doesLabel(instrument, does)))
		self._writeMenu('trigger_does_menu', actions)
		self._writeMenu('menu_items', self._menuItems(targets))
		for i in range(1, logic.NUM_CONNECTIONS + 1):
			self._setMenuSource(self._conPar(i, 'source'), "me.ext.Mappings.menu('con_source', '')")
			self._setMenuSource(self._conPar(i, 'input'), "me.ext.Mappings.menu('con_input', me.par.Con%dsource.eval())" % i)
			self._setMenuSource(self._conPar(i, 'instrument'), "me.ext.Mappings.menu('con_instrument', '')")
			self._setMenuSource(self._conPar(i, 'does'),
				"me.ext.Mappings.doesMenu(me.par.Con%dinstrument.eval(), me.par.Con%dinput.eval())" % (i, i))
		for i in range(1, logic.NUM_TRIGGERS + 1):
			self._setMenuSource(self._triggerPar(i, 'source'), "me.ext.Mappings.menu('trigger_source', '')")
			self._setMenuSource(self._triggerPar(i, 'input'),
				"me.ext.Mappings.menu('trigger_input', me.par.Trig%dsource.eval())" % i)
			self._fitTrigger(i)
		for i in range(1, logic.NUM_SLOTS + 1):
			for field, table in (('signal', 'signal_menu'), ('target', 'target_menu')):
				self._setMenuSource(self._slotPar(i, field),
					"tdu.TableMenu(me.op('%s'), labelCol=1, includeFirstRow=True)" % table)
			self._setMenuSource(self._slotPar(i, 'source'), "me.ext.Mappings.menu('source', '')")
			self._setMenuSource(self._slotPar(i, 'input'), "me.ext.Mappings.menu('input', me.par.Map%dsource.eval())" % i)
			self._setMenuSource(self._slotPar(i, 'instrument'), "me.ext.Mappings.menu('instrument', '')")
			self._setMenuSource(self._slotPar(i, 'setting'),
				"me.ext.Mappings.menu('setting', me.par.Map%dinstrument.eval())" % i)
		self.syncMenus()

	def LoadPreset(self, preset: Optional[str] = None) -> None:
		"""Show preset A-D (default: the Preset parameter) in the slots and send it to the engine."""
		logic = self._logic()
		preset = preset or self.ownerComp.par.Preset.eval()
		slots = self._presets()[preset]
		for i, slot in enumerate(slots, start=1):
			for field in logic.SLOT_FIELDS:
				self._slotPar(i, field).val = slot[field]
		for i, trig in enumerate(self._triggerPresets()[preset], start=1):
			for field in logic.TRIGGER_FIELDS:
				self._triggerPar(i, field).val = trig[field]
			self._fitTrigger(i)
		self.syncMenus()
		self.syncConnections()
		self.writeAssignments()

	def CopyPreset(self, source: str, destination: str) -> None:
		"""Copy every slot of preset source into preset destination."""
		presets = self._presets()
		presets[destination] = [dict(s) for s in presets[source]]
		self._writePresets(presets)
		triggers = self._triggerPresets()
		triggers[destination] = [dict(t) for t in triggers[source]]
		self._writeTriggerPresets(triggers)
		if self.ownerComp.par.Preset.eval() == destination:
			self.LoadPreset(destination)

	def ClearPreset(self, preset: str) -> None:
		"""Empty every slot of a preset."""
		presets = self._presets()
		presets[preset] = self._logic().emptySlots()
		self._writePresets(presets)
		triggers = self._triggerPresets()
		triggers[preset] = self._logic().emptyTriggers()
		self._writeTriggerPresets(triggers)
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
		if field in MENU_FIELDS:
			self._menusToSlot(slot, field)
			return
		if field in ('signal', 'target'):
			self._slotToMenus(slot)
		stored = self._presets()[self.ownerComp.par.Preset.eval()]
		# Every slot, not only this one: callbacks for several changes in one frame
		# arrive one by one, and the first one saves them all.
		for i, (current, old) in enumerate(zip(self._currentSlots(), stored), start=1):
			if current['target'] != old['target']:
				low, high = self._logic().targetRange(current['target'], self._targetRanges())
				self._slotPar(i, 'from').val = low
				self._slotPar(i, 'to').val = high
		if self._currentSlots() != stored:
			self._saveCurrent()
		self.writeAssignments()

	def onTriggerChange(self, par: Par, prev) -> None:
		"""A trigger parameter changed: a new Does gets its usual Amount and slider, Note is greyed out unless When is MIDI; then save.

		Judged against the stored preset, like onSlotChange: values that match
		it came from loading the preset, not from the user.
		"""
		logic = self._logic()
		name = par.name
		digits = ''.join(c for c in name[4:] if c.isdigit())
		field = name[4 + len(digits):]
		if digits and field in TRIGGER_MENU_FIELDS:
			self._menusToTrigger(int(digits), field)
			return
		if digits and field == 'when':
			self._triggerToMenus(int(digits))
		stored = self._triggerPresets()[self.ownerComp.par.Preset.eval()]
		current = self._currentTriggers()
		for i, (now, old) in enumerate(zip(current, stored), start=1):
			if now['does'] != old['does']:
				self._triggerPar(i, 'amount').val = logic.triggerAmount(now['does'])[0]
			self._fitTrigger(i)
		current = self._currentTriggers()
		if current != stored:
			triggers = self._triggerPresets()
			triggers[self.ownerComp.par.Preset.eval()] = current
			self._writeTriggerPresets(triggers)

	def onMidiPreset(self, value: float) -> None:
		"""The engine's mapping_preset changed (a MIDI 'mapping.preset' row): switch preset if following MIDI."""
		if not self.ownerComp.par.Followmidi.eval():
			return
		preset = self._logic().presetFromMidi(value)
		if preset and preset != self.ownerComp.par.Preset.eval():
			self.ownerComp.par.Preset = preset

	def writeAssignments(self) -> None:
		"""Write the current slots as engine rows into the assignments table."""
		logic = self._logic()
		rows = logic.assignmentRows(self._currentSlots()[:logic.NUM_CONNECTIONS], known=self._knownTargets())
		table = self.ownerComp.op('assignments')
		if [[c.val for c in r] for r in table.rows()] != rows:
			table.clear()
			for row in rows:
				table.appendRow(row)

	def menu(self, kind: str, key: str) -> _Menu:
		"""The entries of one of the four menus (menuSource of the slot and trigger menus)."""
		table = self.ownerComp.op('menu_items')
		names, labels = [NONE], [self._text('mapping.none', '-')]
		if table is not None:
			for r in range(1, table.numRows):
				if table[r, 0].val == kind and table[r, 1].val == key:
					names.append(table[r, 2].val)
					labels.append(table[r, 3].val)
		return _Menu(names, labels)

	def syncMenus(self) -> None:
		"""Set every slot's and trigger's menus from its stored signal and target."""
		logic = self._logic()
		for i in range(1, logic.NUM_SLOTS + 1):
			self._slotToMenus(i)
		for i in range(1, logic.NUM_TRIGGERS + 1):
			self._triggerToMenus(i)


	# ------------------------------------------------------------ connections (what students see)

	def onConnectionChange(self, par: Par, prev) -> None:
		"""A connection parameter changed (Con<N><field>): keep its menus valid, then write it into its slot or trigger."""
		digits = ''.join(c for c in par.name[3:] if c.isdigit())
		field = par.name[3 + len(digits):]
		if not digits or self._syncing:
			return
		self._connectionToSlots(int(digits), field)

	def syncConnections(self) -> None:
		"""Set every connection's menus from its stored mapping slot or trigger (after a preset load)."""
		self._syncing = True
		try:
			for i in range(1, self._logic().NUM_CONNECTIONS + 1):
				self._slotsToConnection(i)
		finally:
			run('args[0]._endSync()', self, delayFrames=2)

	def _endSync(self) -> None:
		self._syncing = False

	def _conPar(self, i: int, field: str) -> Par:
		return self.ownerComp.par['Con%d%s' % (i, field)]

	def _connectionKinds(self, i: int) -> tuple:
		return self._logic().inputKinds(self._conPar(i, 'input').eval())

	def _slotsToConnection(self, i: int) -> None:
		"""Mapping slot i (on) or trigger i -> the connection's menus.

		Both on (shows from before connections): the trigger is kept and the
		slot is switched off, as one connection can do one thing.
		"""
		logic = self._logic()
		slot_on = bool(self._slotPar(i, 'on').eval())
		trig_on = bool(self._triggerPar(i, 'on').eval())
		use_trigger = trig_on
		if not slot_on and not trig_on and not self._slotPar(i, 'signal').eval():
			# Both off: show the trigger only when it was set up (not the untouched default).
			default = logic.TRIGGER_DEFAULTS
			use_trigger = (self._triggerPar(i, 'when').eval(), self._triggerPar(i, 'does').eval()) != (default['when'], default['does'])
		if slot_on and trig_on:
			self._slotPar(i, 'on').val = 0
			slot_on = False
		if use_trigger:
			source, name = logic.splitSignal(self._triggerPar(i, 'when').eval())
			instrument, does = logic.connectionAction(self._triggerPar(i, 'does').eval())
			on = trig_on
			self._conPar(i, 'note').val = int(self._triggerPar(i, 'note').eval())
			self._conPar(i, 'amount').val = float(self._triggerPar(i, 'amount').eval())
		else:
			source, name = logic.splitSignal(self._slotPar(i, 'signal').eval())
			instrument, setting = logic.splitTarget(self._slotPar(i, 'target').eval())
			does = 'set:' + setting if setting else NONE
			on = slot_on
		self._setMenu(self._conPar(i, 'source'), source)
		self._setMenu(self._conPar(i, 'input'), name)
		self._setMenu(self._conPar(i, 'instrument'), instrument)
		self._setMenu(self._conPar(i, 'does'), does)
		if bool(self._conPar(i, 'on').eval()) != on:
			self._conPar(i, 'on').val = int(on)
		self._fitConnection(i)

	def _connectionToSlots(self, i: int, field: str) -> None:
		"""The connection's menus -> its mapping slot (Does = controls a setting) or trigger (a one-time action)."""
		logic = self._logic()
		source = self._conPar(i, 'source').eval()
		name = self._conPar(i, 'input').eval()
		inputs = logic.connectionInputs(source) if source != NONE else []
		if field == 'source' and name not in inputs:
			name = inputs[0] if inputs else NONE
			self._setMenu(self._conPar(i, 'input'), name)
		instrument = self._conPar(i, 'instrument').eval()
		does = self._conPar(i, 'does').eval()
		options = [n for n in self.menu('does', self._doesKey(instrument, name)).menuNames if n != NONE]
		if field in ('source', 'input', 'instrument') and does not in options:
			does = options[0] if options else NONE
			self._setMenu(self._conPar(i, 'does'), does)
		signal = logic.joinSignal(source if source != NONE else '', name)
		complete = bool(signal) and instrument != NONE and does != NONE
		if field in ('source', 'input', 'instrument', 'does') and complete and not self._conPar(i, 'on').eval():
			self._conPar(i, 'on').val = 1
		on = int(bool(self._conPar(i, 'on').eval()) and complete)
		if logic.isContinuous(does):
			target = logic.joinTarget(instrument, does[len('set:'):])
			if self._slotPar(i, 'target').eval() != target:
				low, high = logic.targetRange(target, self._targetRanges())
				self._slotPar(i, 'from').val = low
				self._slotPar(i, 'to').val = high
			self._slotPar(i, 'signal').val = signal
			self._slotPar(i, 'target').val = target
			self._slotPar(i, 'on').val = on
			self._triggerPar(i, 'on').val = 0
		else:
			if field in ('instrument', 'does'):
				amount = logic.connectionAmount(instrument, does, self._targetRanges())
				if amount is not None:
					self._conPar(i, 'amount').val = amount[0]
			self._triggerPar(i, 'when').val = signal or 'midi'
			self._triggerPar(i, 'note').val = int(self._conPar(i, 'note').eval())
			self._triggerPar(i, 'does').val = logic.triggerAction(instrument, does) if does != NONE else 'pulse'
			self._triggerPar(i, 'amount').val = float(self._conPar(i, 'amount').eval())
			self._triggerPar(i, 'on').val = on
			self._slotPar(i, 'on').val = 0
		self._fitConnection(i)
		self._fitTrigger(i)
		# Save here: changes made inside a parameter callback do not call the callbacks again.
		preset = self.ownerComp.par.Preset.eval()
		presets = self._presets()
		if presets[preset] != self._currentSlots():
			presets[preset] = self._currentSlots()
			self._writePresets(presets)
		triggers = self._triggerPresets()
		if triggers[preset] != self._currentTriggers():
			triggers[preset] = self._currentTriggers()
			self._writeTriggerPresets(triggers)
		self.writeAssignments()

	def _doesKey(self, instrument: str, name: str) -> str:
		return '%s|%s' % (instrument, '+'.join(self._logic().inputKinds(name)))

	def _fitConnection(self, i: int) -> None:
		"""Amount only for actions that have one (with its slider range); Note only for a song note."""
		logic = self._logic()
		instrument = self._conPar(i, 'instrument').eval()
		does = self._conPar(i, 'does').eval()
		amount = logic.connectionAmount(instrument, does, self._targetRanges())
		midi = self._conPar(i, 'input').eval() == 'midi'
		for par in self._withPanelCopies(self._conPar(i, 'amount')):
			if amount is not None and (par.normMin, par.normMax) != (amount[1], amount[2]):
				par.normMin, par.normMax = amount[1], amount[2]
			if par.enable != (amount is not None):
				par.enable = amount is not None
		for par in self._withPanelCopies(self._conPar(i, 'note')):
			if par.enable != midi:
				par.enable = midi

	# ------------------------------------------------------------ private

	def _setMenuSource(self, par: Par, source: str) -> None:
		if par is not None and par.menuSource != source:
			par.menuSource = source

	def _menuItems(self, targets: list) -> list:
		"""menu_items rows (kind, key, name, label): sources, inputs per source, instruments, settings per instrument."""
		logic = self._logic()
		rows = [('kind', 'key', 'name', 'label')]
		for source in logic.SOURCES:
			rows.append(('source', '', source, self._text('source.' + source, source)))
			for name in logic.sourceInputs(source):
				rows.append(('input', source, name, self._inputLabel(source, name, False)))
		for source in logic.TRIGGER_SOURCES:
			rows.append(('trigger_source', '', source, self._text('source.' + source, source)))
			for name in logic.sourceInputs(source, trigger=True):
				rows.append(('trigger_input', source, name, self._inputLabel(source, name, True)))
		for instrument in logic.instrumentsOf(targets):
			rows.append(('instrument', '', instrument, self._text('instrument.' + instrument, instrument)))
			for setting in logic.settingsOf(instrument, targets):
				rows.append(('setting', instrument, setting, self._settingLabel(instrument, setting)))
		for source in logic.CONNECTION_SOURCES:
			rows.append(('con_source', '', source, self._text('source.' + source, source)))
			for name in logic.connectionInputs(source):
				rows.append(('con_input', source, name, self._connectionInputLabel(source, name)))
		kinds_all = (('moment',), ('continuous',), ('moment', 'continuous'))
		for instrument in logic.instrumentsOf(targets):
			# (the four shape layers come last: older phases still use them)
			rows.append(('con_instrument', '', instrument, self._text('instrument.' + instrument, instrument)))
			settings = logic.settingsOf(instrument, targets)
			for kinds in kinds_all:
				key = '%s|%s' % (instrument, '+'.join(kinds))
				for does in logic.doesOptions(instrument, kinds, settings):
					rows.append(('does', key, does, self._doesLabel(instrument, does)))
		return rows

	def doesMenu(self, instrument: str, name: str) -> _Menu:
		"""The Does menu of a connection (menuSource): what the instrument can do with this input."""
		return self.menu('does', self._doesKey(instrument, name))

	def _connectionInputLabel(self, source: str, name: str) -> str:
		"""'Hit (a moment)' / 'Turn the wrist' / 'In zone 1 / enters zone 1'."""
		kinds = self._logic().inputKinds(name)
		if kinds == ('moment',):
			return self._inputLabel(source, name, True)
		label = self._inputLabel(source, name, False)
		if 'moment' in kinds:
			# 'In zone 1 (1 while there)' -> 'In zone 1 / enters zone 1'
			label = re.sub(r' \(1 [^)]*\)', '', label) + ' / ' + self._inputLabel(source, name, True).lower()
		return label

	def _doesLabel(self, instrument: str, does: str) -> str:
		if does.startswith('set:'):
			return self._text('does.set', 'Controls') + ': ' + self._settingLabel(instrument, does[4:])
		if does.startswith('burst:'):
			return self._text('does.burst', 'Burst') + ': ' + self._settingLabel(instrument, does[6:])
		if does.startswith('count:'):
			return self._text('does.count.' + does[6:], does[6:])
		return self._text('trigger.does.' + does, does)

	def _inputLabel(self, source: str, name: str, trigger: bool) -> str:
		"""'Tilt sideways' for wearable roll: the input's own label, else the signal label without its source."""
		text = self._text('input.trigger.' + name, '') if trigger else ''
		text = text or self._text('input.' + name, '')
		if not text:
			text = self._text('signal.' + self._logic().joinSignal(source, name), name)
			text = text.split(': ', 1)[-1]
		return text[:1].upper() + text[1:]

	def _settingLabel(self, instrument: str, setting: str) -> str:
		text = self._text('setting.' + setting, '')
		if not text:
			text = self._text('target.%s.%s' % (instrument, setting), setting)
			if ': ' in text:
				text = text.split(': ', 1)[1]
			elif instrument.startswith('layer') and text.count(' ') >= 2:
				text = text.split(' ', 2)[2]
		return text[:1].upper() + text[1:]

	def _slotToMenus(self, slot: int) -> None:
		"""Movement / Visual -> the four menus (after a preset load or a typed value)."""
		logic = self._logic()
		source, name = logic.splitSignal(self._slotPar(slot, 'signal').eval())
		instrument, setting = logic.splitTarget(self._slotPar(slot, 'target').eval())
		for field, value in (('source', source), ('input', name), ('instrument', instrument), ('setting', setting)):
			self._setMenu(self._slotPar(slot, field), value)

	def _menusToSlot(self, slot: int, field: str) -> None:
		"""A menu changed: keep Input / Setting valid for the new Source / Instrument, then set Movement / Visual."""
		logic = self._logic()
		source = self._slotPar(slot, 'source').eval()
		name = self._slotPar(slot, 'input').eval()
		inputs = logic.sourceInputs(source)
		if field == 'source' and name not in inputs:
			name = inputs[0] if inputs else NONE
			self._setMenu(self._slotPar(slot, 'input'), name)
		instrument = self._slotPar(slot, 'instrument').eval()
		setting = self._slotPar(slot, 'setting').eval()
		settings = [n for n in self.menu('setting', instrument).menuNames if n != NONE]
		if field == 'instrument' and setting not in settings:
			setting = settings[0] if settings else NONE
			self._setMenu(self._slotPar(slot, 'setting'), setting)
		signal = logic.joinSignal(source if source != NONE else '', name)
		target = logic.joinTarget(instrument if instrument != NONE else '', setting)
		changed = False
		if field in ('source', 'input') and self._slotPar(slot, 'signal').eval() != signal:
			self._slotPar(slot, 'signal').val = signal
			changed = True
		if field in ('instrument', 'setting') and self._slotPar(slot, 'target').eval() != target:
			self._slotPar(slot, 'target').val = target
			changed = True
		# A slot the student has just completed switches on (only on a real change, never on a preset load).
		if changed and signal and target and not self._slotPar(slot, 'on').eval():
			self._slotPar(slot, 'on').val = 1

	def _triggerToMenus(self, trigger: int) -> None:
		source, name = self._logic().splitSignal(self._triggerPar(trigger, 'when').eval())
		self._setMenu(self._triggerPar(trigger, 'source'), source)
		self._setMenu(self._triggerPar(trigger, 'input'), name)

	def _menusToTrigger(self, trigger: int, field: str) -> None:
		logic = self._logic()
		source = self._triggerPar(trigger, 'source').eval()
		name = self._triggerPar(trigger, 'input').eval()
		inputs = logic.sourceInputs(source, trigger=True)
		if field == 'source' and name not in inputs:
			name = inputs[0] if inputs else NONE
			self._setMenu(self._triggerPar(trigger, 'input'), name)
		when = logic.joinSignal(source if source != NONE else '', name)
		if when and self._triggerPar(trigger, 'when').eval() != when:
			self._triggerPar(trigger, 'when').val = when
			if not self._triggerPar(trigger, 'on').eval():
				self._triggerPar(trigger, 'on').val = 1

	def _setMenu(self, par: Par, value: str) -> None:
		"""Set a menu parameter to value ('' = none)."""
		if par is None:
			return
		value = value or NONE
		if par.eval() != value:
			par.val = value

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

	def _triggerPar(self, trigger: int, field: str) -> Par:
		return self.ownerComp.par['Trig%d%s' % (trigger, field)]

	def _fitTrigger(self, trigger: int) -> None:
		"""Fit a trigger's Amount slider to its action, and grey out its Note unless When is a MIDI note.

		The control panel's copies follow (ControlExt also copies enable when it rebuilds).
		"""
		_default, low, high = self._logic().triggerAmount(self._triggerPar(trigger, 'does').eval())
		midi = self._triggerPar(trigger, 'when').eval() == 'midi'
		for par in self._withPanelCopies(self._triggerPar(trigger, 'amount')):
			if (par.normMin, par.normMax) != (low, high):
				par.normMin, par.normMax = low, high
		for par in self._withPanelCopies(self._triggerPar(trigger, 'note')):
			if par.enable != midi:
				par.enable = midi

	def _withPanelCopies(self, par: Par) -> list:
		"""par and the control panel parameters bound to it."""
		pars = [par]
		control = getattr(op, 'Control', None)
		if control is not None:
			pars += [p for p in control.customPars if (p.bindExpr or '').endswith('.par.' + par.name)]
		return pars

	def _currentTriggers(self) -> list:
		logic = self._logic()
		triggers = []
		for i in range(1, logic.NUM_TRIGGERS + 1):
			trig = {}
			for field in logic.TRIGGER_FIELDS:
				par = self._triggerPar(i, field)
				trig[field] = par.eval() if field in logic.TRIGGER_TEXT else float(par.eval())
			triggers.append(trig)
		return triggers

	def _triggerPresets(self) -> dict:
		table = self.ownerComp.op('trigger_presets')
		return self._logic().readTriggers([[c.val for c in r] for r in table.rows()])

	def _writeTriggerPresets(self, presets: dict) -> None:
		rows = self._logic().triggerRows(presets)
		table = self.ownerComp.op('trigger_presets')
		if [[c.val for c in r] for r in table.rows()] != rows:
			table.clear()
			for row in rows:
				table.appendRow(row)

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
		"""Every engine target: layers, master, controls and the instruments' settings."""
		engine = getattr(op, 'Engine', None)
		return engine.op('engine').module.knownTargets() if engine else []

	def _targetRanges(self) -> dict:
		"""The instruments' targets with their slider ranges, for a new slot's From / To."""
		engine = getattr(op, 'Engine', None)
		return engine.op('engine').module.targetRanges() if engine else {}

	def _liveSignals(self) -> list:
		inputs = getattr(op, 'Inputs', None)
		chop = inputs.op('signals') if inputs else None
		return [c.name for c in chop.chans()] if chop is not None else []

	def _text(self, key: str, default: str) -> str:
		lang = getattr(op, 'Lang', None)
		return lang.T(key, default) if lang is not None else default
