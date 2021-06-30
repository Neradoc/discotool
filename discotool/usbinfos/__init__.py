#!/usr/bin/env python3

"""
Find and list USB devices that have a serial port or a certain vendor ID
Match the devices with the serial port and mount point if possible

The main objective is to get informations about Circuitpython boards in particular and Arduino, Adafruit, and microcontroller boards in general

I found no way to use pure python (pyusb, pyserial, psutil, etc.) to link the drive and it's USB device.

the API:
- get_devices_list() returns the list of boards
"""

import sys


if sys.platform == "darwin":
	from .usbinfos_macos import get_devices_list

elif sys.platform == "linux":
	from .usbinfos_linux import get_devices_list

elif sys.platform == "win32":
	from .usbinfos_win32 import get_devices_list

else:
	raise ImportError("Platform not supported")


if __name__ == "__main__":
	import pprint
	deviceList,remainingPorts = get_devices_list(drive_info=True)
	pprint.pprint(deviceList)
	pprint.pprint(remainingPorts)
