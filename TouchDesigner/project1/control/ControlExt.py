"""Control: the one panel dancers and teachers use, instead of the network.

Six tabs: Show, Phases, Instruments, Composition, Movement, Inputs. The panel holds
no values of its own: every control is bound to the parameter it shows on
another component (visuals/particles Energy, inputs Webcamuse, ...), so that
parameter stays the one source of truth, and MIDI, presets and mappings work
exactly as before.

What the panel shows is data, not code: the layout table lists each control
(tab, section, component, parameter, level). Rebuild()
recreates the generated parameters from it whenever Level (Mode: Level 1-2
or Advanced) or Language changes. A row's level is the first Level that
shows it (1 or 2); 0 = Advanced only. Advanced shows every row. Each instrument has its own section on the Instruments
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
LEVELS = {'level1': 1, 'level2': 2, 'advanced': 99}
OWN = ('Mode',)                       # the panel's own setting, never rebuilt
OWN_PAGE = {'Mode': 'show'}
KEEP_PAGES = ('About',)                # Embody's build info, kept last


class ControlExt:
	"""Builds the control panel from the layout table."""

	def __init__(self, ownerComp: COMP) -> None:
		self.ownerComp = ownerComp

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
			par.destroy()
		for key, names in order.items():
			own = [name for name, k in OWN_PAGE.items() if k == key]
			wanted = own + names
			if [p.name for p in pages[key].pars] != wanted:
				pages[key].sort(*wanted)
		comp.sortCustomPages(*[pages[k].name for k in PAGES], *[p.name for p in comp.customPages if p.name in KEEP_PAGES])
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
		return getattr(target.par, row['par'], None) if target is not None else None

	def sourceOf(self, panelPar: Par) -> Optional[Par]:
		"""The parameter a panel control is bound to (used to forward pulses)."""
		for row in self.rows():
			if self._name(row['page'], row['comp'], row['par']) == panelPar.name:
				return self.sourcePar(row)
		return None

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
			par.bindExpr = path
			par.mode = ParMode.BIND
			if source.readOnly:
				par.readOnly = True
		return par

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
			mode.menuLabels = ['Level 1', 'Level 2', 'Advanced']
			mode.val = 'advanced' if value == 'advanced' else (value if value in names else
				('level2' if value == 'level3' else 'level1'))
		mode.default = 'level1'
		mode.help = ('Level 1: music, phases, instruments and triggers (moments: a hit, a note, entering a zone). '
			'Level 2: adds the mappings (a movement continuously changes a setting). Advanced: every setting.')

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
