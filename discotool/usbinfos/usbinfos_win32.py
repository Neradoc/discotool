#!/usr/bin/env python3

import os
import re
import wmi
from .pyserial_list_ports_windows import comports
from .usbinfos_common import *

def filter_port_description(description):
	m = re.match(".*%(.+)%.*", description)
	if m:
		name = m.group(1)
	else:
		name = description
	return name.replace("_"," ").title()

def get_devices_list(drive_info=False):
	remainingPorts = [x for x in comports() if x.vid is not None]
	deviceList = []

	serialNumbers = [{"serial_number": x.serial_number} for x in remainingPorts]
	
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
		serialNumbers.append({"serial_number":physical_disk.SerialNumber})
	
	# how to get the actual list of USB connected devices in a useful way ?
	# for now we take anything with a serial number: serial ports and disk drives
	devices = serialNumbers

	for device in devices:
		curDevice = {}
		deviceVolumes = []
		name = ""
		SN = device['serial_number']

		ttys = []
		vid = "0"
		pid = "0"
		manufacturer = ""
		for port in list(remainingPorts):
			if port.serial_number == SN:
				vid = port.vid
				pid = port.pid
				name = filter_port_description(port.description)
				manufacturer = port.manufacturer
				iface = port.interface or ""
				ttys.append({'dev':port.device,'iface':iface})
				remainingPorts.remove(port)

		if vid == "0": continue

		version = ""
		mains = []
		deviceVolumes = []
		for mount in allMounts:
			if mount["disk"].SerialNumber == device['serial_number']:
				if name == "":
					name = mount["disk"].caption
				for disk in mount["volumes"]:
					volume = disk.DeviceID
					if drive_info:
						mains,version = get_cp_drive_info(volume)
					deviceVolumes.append({
						'mount_point': volume+"\\",
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
	#
	rp = [port.device for port in remainingPorts]
	return (deviceList,rp)
