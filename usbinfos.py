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

import os, json, sys
import subprocess
import serial.tools.list_ports
import psutil

if sys.platform == "linux":
	import pyudev

# Vendor IDs recognized as Arduino / Circuitpython boards
VIDS = [
	0x0483, # STM32 BOOTLOADER PID : 57105
	0x239a, # Adafruit
	0x10c4, # serial to USB ?
	0x0d28, # micro:bit
	0x2341, # Arduino
	0x1209, # https://pid.codes/
	0x303a, # Espressif https://github.com/espressif/usb-pids
]

mainNames = ["code.txt","code.py","main.py","main.txt"]

if sys.platform == "darwin":
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
					ttys.append((port.device,port.interface))
					remainingPorts[num_port] = None
				# no SN, use location ID with standard mac paths
				elif serial_num == "":
					location = subGroup['location_id'][2:].split()[0]
					for locationStr in SERIAL_PREFIXES:
						if port.device.startswith(locationStr+location):
							ttys.append((port.device,port.interface))
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
		remainingPorts = [x for x in serial.tools.list_ports.comports() if x.vid is not None]
		
		# list the mounts to match the mount points
		allMounts = {}
		for part in psutil.disk_partitions():
			allMounts[part.device] = part.mountpoint
		
		# list the devices
		deviceList = readSysProfile(system_profile['SPUSBDataType'], [], allMounts)
		rp = [port.device for port in remainingPorts]
		return (deviceList,rp)

elif sys.platform == "linux":

	def getDeviceList():
		# get drives by mountpoint
		allMounts = {}
		for part in psutil.disk_partitions():
			allMounts[part.device] = part.mountpoint

		remainingPorts = [x for x in serial.tools.list_ports.comports() if x.vid is not None]
		remainingPorts = [port.device for port in rp]
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
			#for ki in device.properties: print(ki,device.properties[ki])
			for child in device.children:
				if child.subsystem == "tty":
					tty = child.get("DEVNAME")
					if tty != None:
						ttys.append(tty)
						if tty in remainingPorts:
							remainingPorts = [port for port in remainingPorts if remainingPorts.device != tty]
				if child.device_type == 'partition':
					# volumeName = child.get('ID_FS_LABEL', '')
					node = child.get('DEVNAME','')
					if node in allMounts:
						volume = allMounts[node]
						mains = []
						for mainFile in mainNames:
							if os.path.exists(os.path.join(volume,mainFile)):
								mains.append(mainFile)
						deviceVolumes.append({
							'mount_point': volume,
							'mains': mains,
						})
			#
			# go through parents and find "devpath", remove matching parents
			def noParent(dev):
				for papa in device.traverse():
					if devpath.startswith(papa.get('DEVPATH')):
						return False
				return True
			deviceList = list(filter(noParent,deviceList))
			#
			if vid not in VIDS and len(ttys) == 0: continue
			#
			#curDevice['devpath'] = devpath
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
else:
	print("ERROR: platform not supported")

if __name__ == "__main__":
	import pprint
	deviceList,remainingPorts = getDeviceList()
	pprint.pprint(deviceList)
	pprint.pprint(remainingPorts)
