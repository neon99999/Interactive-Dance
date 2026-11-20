"""compositor: stacks the visible instruments into the one output image.

Each instrument's Instrument page has On (Visible) and Opacity. The values
come from engine/live (<name>_visible, <name>_opacity), so MIDI and mappings
drive them like any other target. The stacking order is fixed (LAYER_ORDER:
video at the back, then noise, particles, shapes, the trigger shape on top)
and every layer is laid over the ones below with its own alpha, so an
instrument with a transparent background shows the layers under it. A hidden instrument (or one at opacity 0) is in no slot, so
nothing demands its image and it does not cook. SLOTS instruments show at
once; with more visible, the top-most SLOTS win.

Slot 1 is the bottom: comp_slot1 = slot 1 over black, comp_slot2 = slot 2
over comp_slot1, and so on; switch_compose takes the last filled slot.
"""

SLOTS = 4
# Back to front. An instrument not listed goes on top, in name order.
LAYER_ORDER = ('video', 'noise', 'particles', 'shapes', 'layer1', 'layer2', 'layer3', 'layer4', 'trigger')
_cache = {'frame': None, 'layers': []}


def _value(live, name, par, default):
	channel = live[name + '_' + par] if live is not None else None
	return channel.eval() if channel is not None else default


def layers(frame=0):
	"""[(out TOP, opacity, operand)] of the visible instruments, bottom first. Computed once per frame."""
	if _cache['frame'] == absTime.frame:
		return _cache['layers']
	live = op.Engine.op('live')
	found = []
	for comp, pars in op.Engine.op('engine').module.instruments():
		name = comp.name
		out = comp.op('out1')
		opacity = max(0.0, min(1.0, float(_value(live, name, 'opacity', 1.0))))
		if out is None or _value(live, name, 'visible', 0) < 0.5 or opacity <= 0:
			continue
		rank = LAYER_ORDER.index(name) if name in LAYER_ORDER else len(LAYER_ORDER)
		found.append((rank, name, out, opacity, 'over'))
	found.sort(key=lambda f: (f[0], f[1]))
	result = [(out, opacity, operand) for _, _, out, opacity, operand in found[-SLOTS:]]
	_cache['frame'] = absTime.frame
	_cache['layers'] = result
	return result


def count(frame=0):
	"""How many slots are filled: the index for switch_compose (0 = black)."""
	return len(layers())


def slotTop(slot, frame=0):
	"""The image in slot (1 = bottom); black when the slot is empty."""
	found = layers()
	return found[slot - 1][0] if slot <= len(found) else op('bg_black')


def slotOpacity(slot, frame=0):
	found = layers()
	return found[slot - 1][1] if slot <= len(found) else 0.0


def slotOperand(slot, frame=0):
	"""How the slot is laid over the ones below: always over (alpha)."""
	found = layers()
	return found[slot - 1][2] if slot <= len(found) else 'over'
