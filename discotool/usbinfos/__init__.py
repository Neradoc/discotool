#!/usr/bin/env python3

"""
Find and list USB devices that have a serial port or a certain vendor ID
Match the devices with the serial port and mount point if possible

The main objective is to get informations about Circuitpython boards in particular and Arduino, Adafruit, and microcontroller boards in general

I found no way to use pure python (pyusb, pyserial, psutil, etc.) to link the drive and it's USB device.

the API:
- get_devices_list() returns the list of boards
"""

import os
import sys


if sys.platform == "darwin":
	from .usbinfos_macos import get_devices_list as _get_devices_list

elif sys.platform == "linux":
	from .usbinfos_linux import get_devices_list as _get_devices_list

elif sys.platform == "win32":
	from .usbinfos_win32 import get_devices_list as _get_devices_list

else:
	raise ImportError("Platform not supported")


############################################################
# device information class
############################################################
class DeviceInfoDict(dict):
	def __init__(self, device_info):
		super().__init__(device_info.items())
		device_attributes = (
			"vendor_id",
			"product_id",
			"serial_num",
			"manufacturer",
			"name",
			"volumes",
			"ports",
			"version",
		)
		for attr in device_attributes:
			if attr in self:
				setattr(self, attr, self[attr])
			else:
				setattr(self, attr, None)

		self.vid = self.vendor_id
		self.pid = self.product_id

		self.drive = None
		self.volume_name = ""
		if self["volumes"]:
			self.drive = self["volumes"][0]["mount_point"]
			self.volume_name = self["volumes"][0]["name"]
		self.volume = self.drive

		self.data = None
		self.repl = None
		for port in self["ports"]:
			if port["iface"].find("CDC2") >= 0:
				self.data = port["dev"]
			else:
				self.repl = port["dev"]


############################################################
# get lists for things
############################################################
def get_devices_list(drive_info=False):
	liste, ports = _get_devices_list(drive_info)
	return ([DeviceInfoDict(item) for item in liste], ports)


def get_identified_devices(drive_info=False):
	liste, _ = _get_devices_list(drive_info)
	return [DeviceInfoDict(item) for item in liste]


def get_unidentified_ports():
	_, ports = _get_devices_list(drive_info)
	return ports


############################################################
# get filtered lists
############################################################
def devices_by_name(name):
	out = []
	liste = get_identified_devices()
	for dev in liste:
		if dev.name.lower().find(name.lower()) >= 0:
			out.append(dev)
	return out


def devices_by_drive(drive_name):
	out = []
	liste = get_identified_devices()
	for dev in liste:
		if dev.volume_name.lower() == drive_name.lower():
			out.append(dev)
	return out


def devices_by_serial(serial_number):
	out = []
	liste = get_identified_devices()
	for dev in liste:
		if dev.serial_num.lower() == serial_number.lower():
			out.append(dev)
	return out

############################################################
# main for tests
############################################################
if __name__ == "__main__":
	import pprint
	deviceList,remainingPorts = get_devices_list(drive_info=True)
	pprint.pprint(deviceList)
	pprint.pprint(remainingPorts)
