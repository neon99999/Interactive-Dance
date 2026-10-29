"""Serial line parser: turn one line of text from a sensor into named values.

Pure Python with no TouchDesigner imports, so it is unit-tested in plain
Python (tests/test_serial_parse.py).

No protocol is invented: the two layouts most microcontroller sketches
already print are understood.
  name=value pairs  'accel=0.52, zone=1'  or  'accel:0.52 zone:1'
  plain numbers     '0.52,1'  or  '0.52 1'  or  '0.52;1'
Plain numbers are named from the names list ('accel, zone'), otherwise
1, 2, 3 ... Every name gets the prefix, e.g. serial_accel or serial_1.
Pieces that are not numbers are skipped and reported, never raised.
Lines starting with # or [ are log messages ('[imu] ready'), not values,
and are skipped. So are lines with non-printing characters: noise from a
wrong baud rate or a board's boot message, which would otherwise turn into
signals with junk names. For the same reason a name must start the line or
follow a space, comma or semicolon.
"""

import math
import re

_PAIR = re.compile(r'(?:^|(?<=[\s,;]))([A-Za-z_][A-Za-z0-9_.]*)\s*[=:]\s*([^\s,;]+)')
_SPLIT = re.compile(r'[\s,;]+')
_NOISE = re.compile(r'[^\t\x20-\x7e]')


def _number(text):
	try:
		value = float(text)
	except ValueError:
		return None
	return value if not (math.isnan(value) or math.isinf(value)) else None


def parseNames(text):
	"""'accel, zone' -> ['accel', 'zone']."""
	return [n for n in _SPLIT.split(str(text).strip()) if n]


def parseLine(line, names=(), prefix='serial_'):
	"""One line of sensor text -> ({name: value}, [problems])."""
	line = str(line).strip()
	values, problems = {}, []
	if not line or line[0] in '#[':
		return values, problems
	if _NOISE.search(line):
		problems.append('line skipped: non-printing characters (wrong baud rate?)')
		return values, problems
	pairs = _PAIR.findall(line)
	if pairs:
		for name, text in pairs:
			value = _number(text)
			if value is None:
				problems.append('%s: "%s" is not a number' % (name, text))
			else:
				values[prefix + name] = value
		return values, problems
	for i, text in enumerate(t for t in _SPLIT.split(line) if t):
		value = _number(text)
		if value is None:
			problems.append('item %d: "%s" is not a number' % (i + 1, text))
			continue
		name = names[i] if i < len(names) else str(i + 1)
		values[prefix + name] = value
	return values, problems
