#!/usr/bin/env python3

"""
Use pyudev and traverse the USB hierarchy of USB devices, removing the parent ones that can be identified as hubs.
"""

import os, json, sys
import subprocess
import psutil
import pyudev
from serial.tools.list_ports import comports
from .usbinfos_common import *

def get_devices_list(drive_info=False):
	# get drives by mountpoint
	allMounts = {}
	for part in psutil.disk_partitions():
		allMounts[part.device] = part.mountpoint

	remainingPorts = [x for x in comports() if x.vid is not None]
	deviceList = []
	
	context = pyudev.Context()
	devices = context.list_devices(subsystem='usb', DEVTYPE='usb_device')
	for device in devices:
		# skip devices that have a base class of 09 (hubs)
		if device.properties['TYPE'].split("/")[0] == "9":
			continue
		# gather information on the device
		try:
			vid = int(device.get('ID_VENDOR_ID'),16)
		except ValueError:
			vid = 0
		try:
			pid = int(device.get('ID_MODEL_ID'),16)
		except ValueError:
			pid = 0
		devpath = device.get('DEVPATH')
		manufacturer = device.get('ID_VENDOR','')
		name = device.get('ID_MODEL')
		SN = device.get('ID_SERIAL_SHORT','')
		# gather information from the device's subsystems
		deviceVolumes = []
		ttys = []
		version = ""
		mains = []
		for child in device.children:
			# serial port(s)
			if child.subsystem == "tty":
				tty = child.get("DEVNAME")
				if tty != None:
					found = False
					for port in list(remainingPorts):
						if tty == port.device:
							iface = port.interface or ""
							name = port.product or name
							manufacturer = port.manufacturer or manufacturer
							#
							ttys.append({'dev':port.device,'iface':iface})
							remainingPorts.remove(port)
							found = True
					if not found:
						ttys.append({'dev':tty,'iface':""})
			# mouted drive(s)
			if child.device_type == 'partition':
				# volumeName = child.get('ID_FS_LABEL', '')
				node = child.get('DEVNAME','')
				if node in allMounts:
					volume = allMounts[node]
					if drive_info:
						mains,version = get_cp_drive_info(volume)
					deviceVolumes.append({
						'mount_point': volume,
						'mains': mains,
					})
		#
		# go through parents and find "devpath", remove matching parents
		def noParent(dev):
			for papa in device.traverse():
				if devpath.startswith(dev['devpath']):
					return False
			return True
		deviceList = list(filter(noParent,deviceList))
		#
		if vid not in VIDS and len(ttys) == 0: continue
		#
		curDevice = {}
		curDevice['version'] = version
		curDevice['devpath'] = devpath
		curDevice['volumes'] = deviceVolumes
		curDevice['name'] = name
		curDevice['vendor_id'] = vid
		curDevice['product_id'] = pid
		curDevice['serial_num'] = SN
		curDevice['ports'] = ttys
		curDevice['manufacturer'] = manufacturer
		deviceList.append(curDevice)
	#
	for i in range(len(deviceList)):
		del deviceList[i]['devpath']
	rp = [port.device for port in remainingPorts]
	return (deviceList,rp)
