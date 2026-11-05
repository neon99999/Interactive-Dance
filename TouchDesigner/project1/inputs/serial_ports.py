"""Which serial ports exist right now, so Read Serial never opens a missing port.

Opening a port that is not there (Read Serial on, receiver unplugged) froze
TouchDesigner at startup. serial_in.active asks isPresent() first, so a missing
port is simply not opened, and the port opens by itself once the receiver is
plugged in. The list is read at most once a second.

Windows: the ports in the registry (HARDWARE\\DEVICEMAP\\SERIALCOMM), the same
list Device Manager shows. macOS: whether the /dev/... path exists.
"""

import os
import time

CHECK_EVERY_S = 1.0
_cache = {'time': -1e9, 'ports': ()}


def presentPorts():
	"""The serial port names present now, lower case (e.g. ('com3',))."""
	now = time.monotonic()
	if now - _cache['time'] >= CHECK_EVERY_S:
		_cache['time'] = now
		_cache['ports'] = tuple(p.lower() for p in _readPorts())
	return _cache['ports']


def _readPorts():
	try:
		import winreg
	except ImportError:
		return ()
	ports = []
	try:
		key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DEVICEMAP\SERIALCOMM')
	except OSError:
		return ()  # the key only exists while at least one port is present
	with key:
		index = 0
		while True:
			try:
				ports.append(str(winreg.EnumValue(key, index)[1]))
			except OSError:
				break
			index += 1
	return ports


def isPresent(port, frame=0):
	"""True if the port exists now. frame is unused: passing absTime.frame
	makes a parameter expression re-check every frame (cheap, the list is cached)."""
	port = str(port).strip()
	if not port:
		return False
	if port.startswith('/'):
		return os.path.exists(port)
	return port.lower() in presentPorts()
