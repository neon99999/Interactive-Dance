"""panel_clicks: a click on a tile picks the big view; the bar's momentary buttons act."""


def onOffToOn(panelValue):
	comp = panelValue.owner
	if comp.name.startswith('tile_'):
		parent.Stage.ext.Stage.onTileClick(comp)
	else:
		parent.Stage.ext.Stage.onButton(comp)
