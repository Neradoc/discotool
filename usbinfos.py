#!/usr/bin/env python3

"""
Liste les appareils USB adafruit et trouve leur mountpoint et port série USB

On MacOS I found no way to use pure python (pyusb, pyserial, psutil, etc.) to link the drive and it's USB device, so instead we have to call a system specific command (system_profiler) as unsatisfying as it is.

On linux we use pyudev and traverse the USB hierarchy of USB devices, removing the parent ones that can be identified as hubs (they are parent of another device and where already traversed)

On mac we find the microbits volumes by matching the serial number on the volume with the on in the USB. Otherwise the volume does not seem to be listed in system_profiler.

TODO: have a rule to select the serial port used if more than one

the API:
- getDeviceList() returns the list of boards
"""

import os, glob, json, sys
import subprocess
import serial.tools.list_ports

# Vendor IDs recognized as Arduino / Circuitpython boards
VIDS = [
	0x0483, # STM32 BOOTLOADER PID : 57105
	0x239a, # Adafruit
	0x10c4, # serial to USB ?
	0x0d28, # micro:bit
	0x2341, # Arduino
]

mainNames = ["code.txt","code.py","main.py","main.txt"]

if sys.platform == "darwin":
	# look at the MICROBITS volumes and the SN in DETAILS.TXT
	def findMicroBits():
		outListe = {}
		lbits = glob.glob("/Volumes/MICROBIT*")
		for bit in lbits:
			file = bit+"/DETAILS.TXT"
			with open(file,"r") as fp:
				l1 = fp.readline()
				l2 = fp.readline()
				l2 = l2.split(":")[-1].strip()
				outListe[l2] = bit
		return outListe

	def getDeviceList():
		global remainingPorts
		# system_profiler -json SPUSBDataType
		ses = subprocess.check_output(["system_profiler","-json","SPUSBDataType"], stderr=subprocess.DEVNULL)
		system_profile = json.loads(ses)
		
		# list the micro:bit virtual drives (that are somehow not in system_profiler)
		bitsList = findMicroBits()

		# list the existing ports
		remainingPorts = list(filter(lambda x: x.vid != None, serial.tools.list_ports.comports()))
	
		# going recursively through all the devices
		# extracting the important informations
		# skipping the media infos and listing the volumes
		def readSysProfile(profile,devices):
			global remainingPorts
			for subGroup in profile:
				# go depth first
				if "_items" in subGroup:
					devices = readSysProfile(subGroup['_items'],devices)
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
				for x in range(len(remainingPorts)):
					port = remainingPorts[x]
					# has SN, match it with the serial ports
					if port.vid == vid and port.pid == pid \
						and serial_num != "" and port.serial_number == serial_num:
						ttys.append(port.device)
						remainingPorts[x] = None
					# no SN, use location ID with standard mac paths
					elif serial_num == "":
						import pprint
						location = subGroup['location_id'][2:].split()[0]
						locationStr = "/dev/cu.usbmodem"+location
						if port.device.startswith(locationStr):
							ttys.append(port.device)
							remainingPorts[x] = None
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
				# identify and add the micro:bit volumes
				deviceVolumes = []
				if curDevice['name'].find("micro:bit"):
					if serial_num in bitsList:
						bitvolume = {
							'mount_point': bitsList[serial_num],
							'mains': [],
						}
						deviceVolumes.append(bitvolume)
				# list the volume(s) and the circtuipython run files
				version = ""
				if 'Media' in subGroup:
					for media in subGroup['Media']:
						if "volumes" in media:
							# list all the volumes of the media
							for volume in media['volumes']:
								if 'mount_point' in volume:
									mount = volume['mount_point']
									if mount != "":
										mains = []
										for mainFile in mainNames:
											if os.path.exists(os.path.join(mount,mainFile)):
												mains += [mainFile]
										deviceVolumes.append({
											'mount_point': mount,
											'mains': mains,
										})
									boot_out = os.path.join(mount, "boot_out.txt")
									try:
										with open(boot_out) as boot:
											circuit_python, _ = boot.read().split(";")
											version = circuit_python.split(" ")[-3]
									except (FileNotFoundError,ValueError,IndexError):
										pass
				curDevice['volumes'] = deviceVolumes
				curDevice['version'] = version
				devices += [curDevice]
			return devices
		
		# list the devices
		deviceList = readSysProfile(system_profile['SPUSBDataType'],[])
		rp = [port.device for port in remainingPorts]
		return (deviceList,rp)

elif sys.platform == "linux":
	import psutil
	import pyudev

	def getDeviceList():
		# get drives by mountpoint
		mounts = {}
		for part in psutil.disk_partitions():
			mounts[part.device] = part.mountpoint

		rp = list(filter(lambda x: x.vid != None, serial.tools.list_ports.comports()))
		remainingPorts = [port.device for port in rp]
		deviceList = []
		
		context = pyudev.Context()
		devices = context.list_devices(subsystem='usb', DEVTYPE='usb_device')
		for device in devices:
			curDevice = {}
			deviceVolumes = []
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
						if tty in remainingPorts: remainingPorts.remove(tty)
				if child.device_type == 'partition':
					volumeName = child.get('ID_FS_LABEL', '')
					node = child.get('DEVNAME','')
					if node in mounts:
						volume = mounts[node]
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
