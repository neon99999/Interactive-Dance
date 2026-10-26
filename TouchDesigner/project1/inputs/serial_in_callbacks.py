"""Serial callbacks: parse each received line into serial_values (name, value).

The parser is serial_parse (plain Python). Values keep their last reading
until a new line updates them, so an unplugged device simply stops changing.
"""


def onReceive(dat, rowIndex, message, byteData):
	inputs = parent.Inputs
	parser = inputs.op('serial_parse').module
	names = parser.parseNames(inputs.par.Serialnames.eval())
	values, problems = parser.parseLine(message, names)
	table = inputs.op('serial_values')
	for name, value in values.items():
		cell = table[name, 1]
		if cell is None:
			table.appendRow([name, value])
		else:
			cell.val = value
	if problems:
		debug('serial line %r: %s' % (message, '; '.join(problems)))
