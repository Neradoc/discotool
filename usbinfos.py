#!/usr/bin/env python3

"""
Find and list USB devices that have a serial port or a certain vendor ID
Match the devices with the serial port and mount point if possible

The main objective is to get informations about Circuitpython boards in particular and Arduino, Adafruit, and microcontroller boards in general

I found no way to use pure python (pyusb, pyserial, psutil, etc.) to link the drive and it's USB device.

On MacOS we have to call a system specific command (system_profiler). At least it outputs json. We find the serial ports by comparing vid, pid and serial number or location_id with the information from pyserial. Virtual drives that don't appear by name in  SPSUSBDataType are found through psutil.disk_partitions() and their bsd_name.

On linux we use pyudev and traverse the USB hierarchy of USB devices, removing the parent ones that can be identified as hubs.

On mac we find the microbits volumes by matching the serial number on the volume with the on in the USB. Otherwise the volume does not seem to be listed in system_profiler.

TODO: have a rule to select the serial port used if more than one

the API:
- getDeviceList() returns the list of boards
"""

import sys

if sys.platform == "darwin":
	from usbinfos_macos import getDeviceList

elif sys.platform == "linux":
	from usbinfos_linux import getDeviceList

else:
	raise ImportError("Platform not supported")

if __name__ == "__main__":
	import pprint
	deviceList,remainingPorts = getDeviceList()
	pprint.pprint(deviceList)
	pprint.pprint(remainingPorts)
