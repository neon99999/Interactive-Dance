"""Control: the one panel dancers and teachers use, instead of the network.

Five tabs: Show, Instruments, Composition, Movement, Inputs. The panel holds
no values of its own: every control is bound to the parameter it shows on
another component (visuals/particles Energy, inputs Webcamuse, ...), so that
parameter stays the one source of truth, and MIDI, presets and mappings work
exactly as before.

What the panel shows is data, not code: the layout table lists each control
(tab, section, component, parameter, shown in Basic). Rebuild()
recreates the generated parameters from it whenever Mode (Basic / Advanced),
Language changes. Each instrument has its own section on the Instruments
tab (switching one by menu rebuilt the panel and froze it for a second). Labels, help and menus come from the bound
parameter, so they follow the Language switch; tab and section names come
from the lang table (control.page.<id>, control.section.<id>).
Pulses (Reset, Load, Open Output Window) are forwarded by control_pulses.
"""

from typing import Optional

PAGES = ('show', 'instruments', 'composition', 'movement', 'inputs')
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
		"""Recreate the panel's generated controls for the current Mode and Language. Returns how many."""
		comp = self.ownerComp
		for par in list(comp.customPars):
			if par.name not in OWN and par.page.name not in KEEP_PAGES:
				par.destroy()
		pages = {}
		for key in PAGES:
			label = self._text('control.page.' + key, key.title())
			page = next((p for p in comp.customPages if p.name in (label, self._storedPageName(key))), None)
			if page is None:
				page = comp.appendCustomPage(label)
			page.name = label
			pages[key] = page
		comp.store('_pageNames', {k: p.name for k, p in pages.items()})
		self._ensureOwn(pages)
		basicOnly = comp.par.Mode.eval() == 'basic'
		built = 0
		section = {}
		for row in self.rows():
			if basicOnly and not row['basic']:
				continue
			source = self.sourcePar(row)
			if source is None:
				continue
			page = pages[row['page']]
			if section.get(row['page']) != row['section'] and row['section']:
				section[row['page']] = row['section']
				page.appendHeader('H' + self._name(row['page'], row['section'], '').lower(),
					label=self._text('control.section.' + row['section'], row['section'].title()))
			self._appendLike(page, self._name(row['page'], row['comp'], row['par']), source, row)
			built += 1
		comp.sortCustomPages(*[pages[k].name for k in PAGES])
		for name, key in OWN_PAGE.items():
			pages[key].sort(name, *[p.name for p in pages[key].pars if p.name != name])
		pulses = [p.name for p in comp.customPars if p.isPulse]
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
				'basic': table[r, 'basic'].val == '1',
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
			par.menuSource = path
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
		if style != 'Pulse':
			par.default = source.default
			par.bindExpr = path
			par.mode = ParMode.BIND
			if source.readOnly:
				par.readOnly = True
		return par

	def _ensureOwn(self, pages: dict) -> None:
		"""Get-or-create Mode (Show tab)."""
		comp = self.ownerComp
		if getattr(comp.par, 'Mode', None) is None:
			mode = pages['show'].appendMenu('Mode', label='Mode')[0]
			mode.menuNames, mode.menuLabels = ['basic', 'advanced'], ['Basic', 'Advanced']
			mode.default = 'basic'
			mode.val = 'basic'
			mode.help = 'Basic shows the few controls needed on day one. Advanced shows every setting.'

	def _storedPageName(self, key: str) -> str:
		return (self.ownerComp.fetch('_pageNames', {}, storeDefault=False) or {}).get(key, '')

	def _name(self, page: str, comp: str, par: str) -> str:
		"""A unique, valid parameter name: tab + component + parameter, e.g. Instparticlesenergy."""
		raw = (page[:4] + comp.split('/')[-1] + par).lower()
		return (''.join(ch for ch in raw if ch.isalnum())).capitalize()

	def _text(self, key: str, default: str) -> str:
		lang = getattr(op, 'Lang', None)
		return lang.T(key, default) if lang is not None else default
