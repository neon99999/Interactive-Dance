"""Control: the one panel dancers and teachers use, instead of the network.

Six tabs: Show, Phases, Instruments, Composition, Movement, Inputs. The panel holds
no values of its own: every control is bound to the parameter it shows on
another component (visuals/particles Energy, inputs Webcamuse, ...), so that
parameter stays the one source of truth, and MIDI, presets and mappings work
exactly as before.

What the panel shows is data, not code: the layout table lists each control
(tab, section, component, parameter, level). Rebuild()
recreates the generated parameters from it whenever Level (Mode: Basic or
Advanced) or Language changes. A row's level is 1 (Basic: what students
need) or 0 (Advanced only). Advanced shows every row. A colour (RGB)
parameter is one row (Colour1), shown as one colour control. Each instrument has its own section on the Instruments
tab (switching one by menu rebuilt the panel and froze it for a second). Labels, help and menus come from the bound
parameter, so they follow the Language switch; tab and section names come
from the lang table (control.page.<id>, control.section.<id>).
Pulses (Reset, Load, Open Output Window) are forwarded by control_pulses.
The stage's panel (stage/controls) has Sync Page on: it shows this COMP's
current page and a tab click sets it, so a refresh of the panel (a parameter
whose menu, range or enable state changes) keeps the tab instead of jumping
back to Show. Rebuild keeps the tab too.
"""

from typing import Optional

PAGES = ('show', 'phases', 'instruments', 'composition', 'movement', 'inputs')
LEVELS = {'basic': 1, 'advanced': 99}
OWN = ('Mode',)                       # the panel's own setting, never rebuilt
OWN_PAGE = {'Mode': 'show'}
KEEP_PAGES = ('About',)                # Embody's build info, kept last
# Parameters that change by themselves (status lines, the playback position)
# are copied, not bound: the panel redraws whenever a shown value changes,
# and a redraw of the stage panel costs tens of ms, so a value that changes
# every frame cut the frame rate in half. refreshStatus() copies them a few
# times a second, and only when the text changed.
COPY_PARS = (('transport', 'Position'),)  # (component, parameter)


class ControlExt:
	"""Builds the control panel from the layout table."""

	def __init__(self, ownerComp: COMP) -> None:
		self.ownerComp = ownerComp
		self._copies = None  # [(panel par name, source Par)], made by refreshStatus, reset by Rebuild

	def onDestroyTD(self) -> None:
		pass

	def onInitTD(self) -> None:
		pass

	def Rebuild(self) -> int:
		"""Bring the panel's generated controls up to date for the current Level and Language. Returns how many.

		Controls that already exist with the right style are kept and only
		updated where they differ (labels, help, menus, ranges): creating and
		destroying hundreds of parameters took several seconds.
		"""
		comp = self.ownerComp
		self._copies = None
		shown = self._shownPageKey()
		pages = {}
		for key in PAGES:
			label = self._text('control.page.' + key, key.title())
			page = next((p for p in comp.customPages if p.name in (label, self._storedPageName(key))), None)
			if page is None:
				page = comp.appendCustomPage(label)
			if page.name != label:
				page.name = label
			pages[key] = page
		comp.store('_pageNames', {k: p.name for k, p in pages.items()})
		self._ensureOwn(pages)
		level = LEVELS.get(comp.par.Mode.eval(), 1)
		existing = {p.name: p for p in comp.customPars if p.name not in OWN and p.page.name not in KEEP_PAGES}
		order = {key: [] for key in PAGES}
		built = 0
		section = {}
		for row in self.rows():
			if level < 99 and not 0 < row['level'] <= level:
				continue
			source = self.sourcePar(row)
			if source is None:
				continue
			page = pages[row['page']]
			if section.get(row['page']) != row['section'] and row['section']:
				section[row['page']] = row['section']
				name = 'H' + self._name(row['page'], row['section'], '').lower()
				label = self._text('control.section.' + row['section'], row['section'].title())
				header = existing.pop(name, None)
				if header is not None and header.page != page:
					header.destroy()
					header = None
				if header is None:
					header = page.appendHeader(name, label=label)[0]
				elif header.label != label:
					header.label = label
				order[row['page']].append(name)
			name = self._name(row['page'], row['comp'], row['par'])
			if source.style in ('RGB', 'RGBA'):
				parts = [existing.pop(name + c, None) for c in 'rgb']
				if any(p is None or p.page != page for p in parts):
					for p in parts:
						if p is not None and p.valid:
							p.destroy()
					self._appendColour(page, name, source, row)
				else:
					self._matchSource(parts[0], source)
				order[row['page']] += [name + c for c in 'rgb']
				built += 1
				continue
			par = existing.pop(name, None)
			if par is not None and (par.style != source.style or par.page != page):
				par.destroy()
				par = None
			if par is None:
				self._appendLike(page, name, source, row)
			else:
				self._matchSource(par, source)
			order[row['page']].append(name)
			built += 1
		for par in existing.values():
			if par.valid:  # destroying one part of a colour destroys all three
				par.destroy()
		for key, names in order.items():
			own = [name for name, k in OWN_PAGE.items() if k == key]
			wanted = own + names
			if [p.name for p in pages[key].pars] != wanted:
				pages[key].sort(*wanted)
		# A tab with nothing on it at this Level (Instruments in Basic) is removed; Advanced makes it again.
		for key in PAGES:
			if not order[key] and not [n for n, k in OWN_PAGE.items() if k == key]:
				pages.pop(key).destroy()
		comp.sortCustomPages(*[pages[k].name for k in PAGES if k in pages], *[p.name for p in comp.customPages if p.name in KEEP_PAGES])
		pulses = [p.name for p in comp.customPars if p.isPulse]
		if shown in pages:
			comp.currentPage = pages[shown]
		watcher = comp.op('control_pulses')
		if watcher is not None:
			watcher.par.pars = ' '.join(list(OWN) + pulses)
		return built

	def OpenPanel(self) -> None:
		"""Open the control panel as a floating parameter window."""
		self.ownerComp.openParameters()

	def rows(self) -> list:
		"""The layout table as a list of dicts."""
		table = self.ownerComp.op('layout')
		out = []
		for r in range(1, table.numRows):
			out.append({
				'page': table[r, 'page'].val, 'section': table[r, 'section'].val,
				'comp': table[r, 'comp'].val, 'par': table[r, 'par'].val,
				'level': int(table[r, 'level'].val or 0),
			})
		return out

	def sourcePar(self, row: dict) -> Optional[Par]:
		"""The parameter a layout row shows, or None if its component or parameter is missing."""
		target = self.ownerComp.parent().op(row['comp'])
		if target is None:
			return None
		# A colour row (Colour1) names the tuplet: its first part (Colour1r) stands for it.
		par = target.par[row['par']]
		return par if par is not None else target.par[row['par'] + 'r']  # (a Par's truth is its value: test None)

	def sourceOf(self, panelPar: Par) -> Optional[Par]:
		"""The parameter a panel control is bound to (used to forward pulses)."""
		for row in self.rows():
			if self._name(row['page'], row['comp'], row['par']) == panelPar.name:
				return self.sourcePar(row)
		return None

	def _appendColour(self, page, name: str, source: Par, row: dict) -> None:
		"""A colour control bound part by part to an RGB parameter (Colour1 -> Colour1r/g/b)."""
		parts = page.appendRGB(name, label=source.label)
		for par, c in zip(parts, 'rgb'):
			par.bindExpr = "me.parent().op('%s').par.%s%s" % (row['comp'], row['par'], c)
			par.mode = ParMode.BIND
			par.help = source.help

	def onOwnChange(self, par: Par, prev) -> None:
		"""Mode changed: rebuild next frame (not inside the callback that destroys pars)."""
		run('args[0].Rebuild()', self.ownerComp, delayFrames=1)

	def _appendLike(self, page, name: str, source: Par, row: dict) -> Par:
		"""Append a control shaped like source and bind it (pulses are forwarded instead)."""
		style = source.style
		path = "me.parent().op('%s').par.%s" % (row['comp'], row['par'])
		if style == 'Pulse':
			par = page.appendPulse(name, label=source.label)[0]
		elif style == 'Momentary':
			par = page.appendMomentary(name, label=source.label)[0]
		elif style == 'Toggle':
			par = page.appendToggle(name, label=source.label)[0]
		elif style in ('Menu', 'StrMenu'):
			par = (page.appendMenu if style == 'Menu' else page.appendStrMenu)(name, label=source.label)[0]
			self._copyMenu(par, source, path)
		elif style == 'Int':
			par = page.appendInt(name, label=source.label)[0]
		elif style == 'Float':
			par = page.appendFloat(name, label=source.label)[0]
		elif style == 'File':
			par = page.appendFile(name, label=source.label)[0]
		elif style == 'Folder':
			par = page.appendFolder(name, label=source.label)[0]
		else:
			par = page.appendStr(name, label=source.label)[0]
		if style in ('Int', 'Float'):
			par.normMin, par.normMax = source.normMin, source.normMax
			par.min, par.max = source.min, source.max
			par.clampMin, par.clampMax = source.clampMin, source.clampMax
		par.help = source.help
		par.enable = source.enable
		if style != 'Pulse':
			par.default = source.default
			if self._isCopy(source):
				par.val = source.eval()
				par.readOnly = True
			else:
				par.bindExpr = path
				par.mode = ParMode.BIND
				if source.readOnly:
					par.readOnly = True
		return par

	def _isCopy(self, source: Par) -> bool:
		"""True for a parameter that changes by itself (copied a few times a second, not bound)."""
		return source.readOnly or (source.owner.name, source.name) in COPY_PARS

	def refreshStatus(self) -> None:
		"""Copy the status lines and the playback position into the panel, only where they changed."""
		comp = self.ownerComp
		if self._copies is None:
			self._copies = []
			for row in self.rows():
				source = self.sourcePar(row)
				if source is not None and self._isCopy(source):
					self._copies.append((self._name(row['page'], row['comp'], row['par']), source))
		for name, source in self._copies:
			par = comp.par[name]
			if par is None or par.mode != ParMode.CONSTANT or not source.valid:
				continue
			value = source.eval()
			if isinstance(value, float):
				value = round(value, 1)
			if par.eval() != value:
				par.val = value

	def _copyMenu(self, par: Par, source: Par, path: str) -> None:
		"""Give a panel menu its source's entries.

		Mostly a copy, not a menuSource: hundreds of menu sources made every
		Rebuild re-evaluate them all for each new parameter (8 s instead of 1);
		Language changes and the mapping page's Refresh rebuild the panel. A
		live device list (serial ports, cameras: a menuSource that is not a
		table) stays live, or the panel would keep the ports of the computer
		that last saved the project.
		"""
		live = bool(source.menuSource) and 'TableMenu' not in source.menuSource
		if live:
			if par.menuSource != path:
				par.menuSource = path
			return
		if par.menuSource:
			par.menuSource = ''
		if list(par.menuNames) != list(source.menuNames) or list(par.menuLabels) != list(source.menuLabels):
			par.menuNames, par.menuLabels = source.menuNames, source.menuLabels

	def _matchSource(self, par: Par, source: Par) -> None:
		"""Update a kept control where it differs from its source (labels and menus follow the Language)."""
		if self._isCopy(source) and par.mode == ParMode.BIND:
			# Unbinding can write through to the source and turn its expression into a constant: keep it.
			mode, expr = source.mode, source.expr
			par.mode = ParMode.CONSTANT
			par.bindExpr = ''
			par.readOnly = True
			if mode == ParMode.EXPRESSION and source.mode != ParMode.EXPRESSION:
				source.expr = expr
				source.mode = ParMode.EXPRESSION
		if par.label != source.label:
			par.label = source.label
		if par.help != source.help:
			par.help = source.help
		if par.enable != source.enable:
			par.enable = source.enable
		if par.isMenu:
			self._copyMenu(par, source, par.bindExpr)
		if source.style in ('Int', 'Float') and (par.normMin, par.normMax) != (source.normMin, source.normMax):
			par.normMin, par.normMax = source.normMin, source.normMax

	def _ensureOwn(self, pages: dict) -> None:
		"""Get-or-create Mode, shown as Level (Show tab): Level 1-2 reveal the tools step by step, Advanced shows all."""
		comp = self.ownerComp
		mode = getattr(comp.par, 'Mode', None)
		if mode is None:
			mode = pages['show'].appendMenu('Mode', label='Level')[0]
		names = list(LEVELS)
		if list(mode.menuNames) != names:
			value = str(mode.eval())
			mode.menuNames = names
			mode.menuLabels = ['Basic', 'Advanced']
			mode.val = 'advanced' if value == 'advanced' else 'basic'
		mode.default = 'basic'
		mode.help = ('Basic: what students need (music, phases, which instruments are on, the connections, '
			'inputs on or off). Advanced: every setting.')

	def _shownPageKey(self) -> str:
		"""The tab the panel shows now (stage/controls has Sync Page on, so it is this COMP's current page)."""
		names = self.ownerComp.fetch('_pageNames', {}, storeDefault=False) or {}
		current = self.ownerComp.currentPage.name
		return next((key for key, name in names.items() if name == current), '')

	def _storedPageName(self, key: str) -> str:
		return (self.ownerComp.fetch('_pageNames', {}, storeDefault=False) or {}).get(key, '')

	def _name(self, page: str, comp: str, par: str) -> str:
		"""A unique, valid parameter name: tab + component + parameter, e.g. Instparticlesenergy."""
		raw = (page[:4] + comp.split('/')[-1] + par).lower()
		return (''.join(ch for ch in raw if ch.isalnum())).capitalize()

	def _text(self, key: str, default: str) -> str:
		lang = getattr(op, 'Lang', None)
		return lang.T(key, default) if lang is not None else default
