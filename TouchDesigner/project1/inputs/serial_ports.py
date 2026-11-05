"""Which serial ports can be opened safely, so Read Serial never hangs TouchDesigner.

Two kinds of port froze TouchDesigner while Read Serial was on:
- a port that is not there (the receiver unplugged);
- on LAPTOP, COM3 with nothing plugged in: it froze until Read Serial was
  turned off. Most likely a Bluetooth serial port, which Windows lists like
  any other but which blocks while it tries to connect (not yet confirmed).
serial_in.active asks isPresent() first, so neither is opened. The receiver is
a USB port, so it opens by itself once plugged in. The list is read at most
once a second. Read Serial also starts off; it is turned on per computer.

Windows: the ports in the registry (HARDWARE\\DEVICEMAP\\SERIALCOMM): the
value name is the driver's device (\\Device\\BthModem0 for Bluetooth,
\\Device\\Silabser0 or \\Device\\USBSER000 for USB), the value the COM name.
macOS: whether the /dev/... path exists.
"""

import os
import time

CHECK_EVERY_S = 1.0
_cache = {'time': -1e9, 'ports': {}}


def presentPorts():
	"""The serial ports present now: {'com3': '\\device\\bthmodem0', ...}, lower case."""
	now = time.monotonic()
	if now - _cache['time'] >= CHECK_EVERY_S:
		_cache['time'] = now
		_cache['ports'] = {name.lower(): device.lower() for device, name in _readPorts()}
	return _cache['ports']


def _readPorts():
	"""(device, COM name) pairs from the registry; empty when not on Windows."""
	try:
		import winreg
	except ImportError:
		return []
	ports = []
	try:
		key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DEVICEMAP\SERIALCOMM')
	except OSError:
		return []  # the key only exists while at least one port is present
	with key:
		index = 0
		while True:
			try:
				device, name, _ = winreg.EnumValue(key, index)
			except OSError:
				break
			ports.append((str(device), str(name)))
			index += 1
	return ports


def portState(port, frame=0):
	"""'ok', 'missing' or 'bluetooth' (listed, but not safe to open).
	frame is unused: passing absTime.frame makes a parameter expression
	re-check every frame (cheap, the list is cached)."""
	port = str(port).strip()
	if not port:
		return 'missing'
	if port.startswith('/'):
		return 'ok' if os.path.exists(port) else 'missing'
	device = presentPorts().get(port.lower())
	if device is None:
		return 'missing'
	return 'bluetooth' if 'bth' in device else 'ok'


def isPresent(port, frame=0):
	"""True if the port can be opened: it exists and is not a Bluetooth port."""
	return portState(port) == 'ok'


def statusText(enabled, port, frame=0):
	"""The Serial page's Status line."""
	if not enabled:
		return 'Off'
	name = str(port).strip().upper() or '(no port)'
	state = portState(port)
	if state == 'ok':
		return 'Reading ' + name
	if state == 'bluetooth':
		return name + ' is a Bluetooth port, not the receiver: pick another Port'
	return name + ' not found: plug in the receiver'
