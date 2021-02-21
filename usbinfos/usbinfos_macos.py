#!/usr/bin/env python3

import os, json, sys
import subprocess
import psutil
#from serial.tools.list_ports import comports
from .pyserial_list_ports_osx import comports
from .usbinfos_common import *

# where to find serial ports named by location on macOS
# NOTE: we don't check for /dev/tty.usbmodem<serial_num>
#       because devices with serial numbers are found differently
SERIAL_PREFIXES = ["/dev/cu.usbmodem","/dev/cu.usbserial-"]

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

# going recursively through all the devices
# extracting the important informations
# skipping the media infos and listing the volumes
def readSysProfile(profile,devices,allMounts):
	global remainingPorts
	for subGroup in profile:
		# go depth first
		if "_items" in subGroup:
			devices = readSysProfile(subGroup['_items'],devices,allMounts)
		subGroup['_items'] = None
		# back to the device
		curDevice = {}
		# vid is required
		if 'vendor_id' not in subGroup:
			continue
		try:
			vid = int(subGroup['vendor_id'].split(" ")[0],16)
		except:
			vid = 0
			continue
		curDevice['vendor_id'] = vid
		# product id
		try:
			pid = int(subGroup['product_id'].strip().split(" ")[0],16)
		except:
			pid = 0
		curDevice['product_id'] = pid
		# serial number is not always present
		if 'serial_num' in subGroup:
			serial_num = subGroup['serial_num']
		else:
			serial_num = ""
		curDevice['serial_num'] = serial_num
		# manufacturer is kind of a mess sometimes
		if 'manufacturer' in subGroup:
			manufacturer = subGroup['manufacturer']
		else:
			manufacturer = ""
		curDevice['manufacturer'] = manufacturer
		# try to guess the port using the Location ID or Serial Number
		ttys = []
		for num_port,port in enumerate(remainingPorts):
			port = remainingPorts[num_port]
			# has SN, match it with the serial ports
			if port.vid == vid and port.pid == pid \
				and serial_num != "" and port.serial_number == serial_num:
				ttys.append({'dev':port.device,'iface':port.interface})
				remainingPorts[num_port] = None
			# no SN, use location ID with standard mac paths
			elif serial_num == "":
				location = subGroup['location_id'][2:].split()[0]
				for locationStr in SERIAL_PREFIXES:
					if port.device.startswith(locationStr+location):
						ttys.append({'dev':port.device,'iface':port.interface})
						remainingPorts[num_port] = None
		remainingPorts = list(filter(lambda x:  x is not None, remainingPorts))
		curDevice['ports'] = ttys
		#
		# now we select all the ones with a known VID or with an existing tty
		# (or skip the others if you will) as soon as possible
		#
		if not (vid in VIDS or len(ttys)>0):
			continue
		# name needs no underscore
		curDevice['name'] = subGroup['_name']
		# list the volume(s) and the circtuipython run files
		deviceVolumes = []
		version = ""
		if 'Media' in subGroup:
			for media in subGroup['Media']:
				if "volumes" in media:
					# list all the volumes of the media
					for volume in media['volumes']:
						if 'mount_point' in volume:
							mount = volume['mount_point']
							mains,version = get_cp_drive_info(mount)
							deviceVolumes.append({
								'mount_point': mount,
								'mains': mains,
							})
				if 'bsd_name' in media:
					disk = os.path.join("/dev",media['bsd_name'])
					if disk in allMounts:
						mount = allMounts[disk]
						mains,version = get_cp_drive_info(mount)
						deviceVolumes.append({
							'mount_point': mount,
							'mains': mains,
						})
		curDevice['volumes'] = deviceVolumes
		curDevice['version'] = version
		devices += [curDevice]
	return devices

def getDeviceList():
	global remainingPorts
	# system_profiler -json SPUSBDataType
	ses = subprocess.check_output(["system_profiler","-json","SPUSBDataType"], stderr=subprocess.DEVNULL)
	system_profile = json.loads(ses)
	
	# list the existing ports
	remainingPorts = [x for x in comports() if x.vid is not None]
	
	# list the mounts to match the mount points
	allMounts = {}
	for part in psutil.disk_partitions():
		allMounts[part.device] = part.mountpoint
	
	# list the devices
	deviceList = readSysProfile(system_profile['SPUSBDataType'], [], allMounts)
	rp = [port.device for port in remainingPorts]
	return (deviceList,rp)
