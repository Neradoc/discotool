#!/usr/bin/env python3

import os, json, sys
import ctypes
import subprocess
import psutil
import wmi
from .pyserial_list_ports_windows import comports
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
	remainingPorts = [x for x in comports() if x.vid is not None]
	deviceList = []
	
	allMounts = []
	wmi_info = wmi.WMI()
	for physical_disk in wmi_info.Win32_DiskDrive ():
		if physical_disk.InterfaceType != "USB": continue
		volumes = []
		for partition in physical_disk.associators ("Win32_DiskDriveToDiskPartition"):
			for logical_disk in partition.associators ("Win32_LogicalDiskToPartition"):
				if logical_disk.DriveType == 2: # removable
					volumes.append(logical_disk)
		allMounts.append({
			"disk": physical_disk,
			"volumes": volumes,
		})
	
	# ici on veut la liste des devices USB - comment ?
	devices = allMounts

	for device in devices:
		curDevice = {}
		deviceVolumes = []
		name = device["disk"].caption
		SN = device["disk"].SerialNumber

		ttys = []
		vid = "0"
		pid = "0"
		manufacturer = ""
		for x,port in enumerate(remainingPorts):
			if port.serial_number == SN:
				vid = port.vid
				pid = port.pid
				manufacturer = port.manufacturer
				iface = port.interface or ""
				ttys.append({'dev':port.device,'iface':iface})
				remainingPorts[x] = None
		
		remainingPorts = [port for port in remainingPorts if port != None]

		if vid == "0": continue

		version = ""
		deviceVolumes = []

		for disk in device["volumes"]:
			volume = disk.DeviceID
			mains,version = get_cp_drive_info(volume)
			deviceVolumes.append({
				'mount_point': volume,
				'mains': mains,
			})
		
		curDevice['version'] = version
		curDevice['volumes'] = deviceVolumes
		curDevice['name'] = name
		curDevice['vendor_id'] = int(vid)
		curDevice['product_id'] = int(pid)
		curDevice['serial_num'] = SN
		curDevice['ports'] = ttys
		curDevice['manufacturer'] = manufacturer
		deviceList.append(curDevice)
		continue

		#for ki in device.properties: print(ki,device.properties[ki])
		for child in device.children:
			if child.subsystem == "tty":
				tty = child.get("DEVNAME")
				if tty != None:
					found = False
					for x,port in enumerate(remainingPorts):
						if tty == port.device:
							iface = port.interface or ""
							ttys.append({'dev':port.device,'iface':iface})
							remainingPorts[x] = None
							found = True
					remainingPorts = [port for port in remainingPorts if port != None]
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
	return (deviceList,remainingPorts)
