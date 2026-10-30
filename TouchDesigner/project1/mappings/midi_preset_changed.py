"""midi_preset_changed: the engine's mapping_preset (set by MIDI rows) switches the preset."""


def onValueChange(channel, sampleIndex, val, prev):
	parent.Mappings.ext.Mappings.onMidiPreset(val)
