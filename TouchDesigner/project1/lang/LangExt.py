"""Language: Spanish / English text for everything dancers see.

The strings table holds one row per text: key, en, es. Keys:
  <comp>.<Parname>.label / .help / .menu   relabel a custom parameter of
                                           /project1/<comp> (menu: labels
                                           separated by |, in menu order)
  anything else                            free text read with T(), e.g. by
                                           panels: op.Lang.T('pose.title')

Switching Language applies every parameter row (Apply) and panels that read
T() during their cook follow on their own (they depend on the table and the
Language parameter). A missing Spanish text falls back to English.
"""

from typing import Optional

LANGUAGES = ('en', 'es')


class LangExt:
	"""Looks up texts in the strings table and relabels parameters for the chosen language."""

	def __init__(self, ownerComp: COMP) -> None:
		self.ownerComp = ownerComp

	def onDestroyTD(self) -> None:
		pass

	def onInitTD(self) -> None:
		pass

	def T(self, key: str, default: Optional[str] = None) -> str:
		"""Text for key in the current language; English if the translation is blank; default (or key) if unknown."""
		table = self.ownerComp.op('strings')
		lang = self.ownerComp.par.Language.eval()
		row = table.row(key) if table is not None else None
		if row is None:
			return key if default is None else default
		cell = table[key, lang]
		text = cell.val if cell is not None else ''
		return text if text else table[key, 'en'].val

	def Apply(self) -> int:
		"""Relabel every parameter named in the strings table. Returns how many were changed."""
		table = self.ownerComp.op('strings')
		project = self.ownerComp.parent()
		changed = 0
		for r in range(1, table.numRows):
			parts = table[r, 'key'].val.split('.')
			if len(parts) != 3 or parts[2] not in ('label', 'help', 'menu'):
				continue
			comp = project.op(parts[0])
			par = comp.par[parts[1]] if comp is not None else None
			if par is None:
				continue
			text = self.T(table[r, 'key'].val)
			if parts[2] == 'label':
				par.label = text
			elif parts[2] == 'help':
				par.help = text
			elif par.isMenu:
				labels = text.split('|')
				if len(labels) == len(par.menuNames):
					par.menuLabels = labels
			changed += 1
		return changed
