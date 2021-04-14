#!/usr/bin/env python3

import os, json, sys
import subprocess
import psutil
import pyudev
from serial.tools.list_ports import comports
from .usbinfos_common import *

# list the drive info for a circuipython drive (code or main and version)
def get_cp_drive_info(mount):
	mains = []
	for mainFile in mainNames:
		if os.path.exists(os.path.join(mount,mainFile)):
			mains += [mainFile]
	boot_out = os.path.join(mount, "boot_out.txt")
	try:
		with open(boot_out) as boot:
			circuit_python, _ = boot.read().split(";")
			version = circuit_python.split(" ")[-3]
	except (FileNotFoundError,ValueError,IndexError):
		version = ""
	return (mains,version)

def getDeviceList():
	# get drives by mountpoint
	allMounts = {}
	for part in psutil.disk_partitions():
		allMounts[part.device] = part.mountpoint

	remainingPorts = [x for x in comports() if x.vid is not None]
	deviceList = []
	
	context = pyudev.Context()
	devices = context.list_devices(subsystem='usb', DEVTYPE='usb_device')
	for device in devices:
		curDevice = {}
		deviceVolumes = []
		# skip devices that have a base class of 09 (hubs)
		if device.properties['TYPE'].split("/")[0] == "9":
			continue
		name = device.get('ID_MODEL')
		vid = int(device.get('ID_VENDOR_ID'),16)
		SN = device.get('ID_SERIAL_SHORT','')
		devpath = device.get('DEVPATH')
		ttys = []
		version = ""
		#for ki in device.properties: print(ki,device.properties[ki])
		for child in device.children:
			if child.subsystem == "tty":
				tty = child.get("DEVNAME")
				if tty != None:
					found = False
					for port in list(remainingPorts):
						if tty == port.device:
							iface = port.interface or ""
							ttys.append({'dev':port.device,'iface':iface})
							remainingPorts.remove(port)
							found = True
					if not found:
						ttys.append({'dev':tty,'iface':""})
			if child.device_type == 'partition':
				# volumeName = child.get('ID_FS_LABEL', '')
				node = child.get('DEVNAME','')
				if node in allMounts:
					volume = allMounts[node]
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
		curDevice['version'] = version
		curDevice['devpath'] = devpath
		curDevice['volumes'] = deviceVolumes
		curDevice['name'] = name
		curDevice['vendor_id'] = vid
		curDevice['product_id'] = int(device.get('ID_MODEL_ID'),16)
		curDevice['serial_num'] = SN
		curDevice['ports'] = ttys
		curDevice['manufacturer'] = device.get('ID_VENDOR','')
		deviceList.append(curDevice)
	#
	for i in range(len(deviceList)):
		del deviceList[i]['devpath']
	return (deviceList,remainingPorts)
