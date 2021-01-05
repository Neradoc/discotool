#!/usr/bin/env python3

"""
Liste les appareils USB adafruit et trouve leur mountpoint et port série USB

I found no way to use pure python (pyusb, pyserial, psutil, etc.) to link the drive and it's USB device, so instead we have to call a system specific command (system_profiler) as unsatisfying as it is.

TODO: have a rule to select the serial port used if more than one

the API:
- getDeviceList() returns the list of boards
"""

import os, glob, json, sys
import subprocess
import serial.tools.list_ports

# Vendor IDs recognized as Arduino / Circuitpython boards
VIDS = [
	"0x0483", # STM32 BOOTLOADER PID : 57105
	"0x239a", # Adafruit ?
	"0x10c4", # serial to USB ?
	"0x0d28", # micro:bit
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
		# system_profiler -json SPUSBDataType
		ses = subprocess.check_output(["system_profiler","-json","SPUSBDataType"], stderr=subprocess.DEVNULL)
		system_profile = json.loads(ses)
	
		# going recursively through all the devices
		# extracting the important informations
		# skipping the media infos and listing the volumes
		def readSysProfile(profile,devices):
			for subGroup in profile:
				# go depth first
				if "_items" in subGroup:
					devices = readSysProfile(subGroup['_items'],devices)
				subGroup['_items'] = None
				# back to the device
				device = {}
				# name needs no underscore
				device['name'] = subGroup['_name']
				# get all the variables
				for ki in subGroup:
					device[ki] = subGroup[ki]
				# explore every media but don't save their parameters
				device['volumes'] = []
				if 'Media' in subGroup:
					for media in subGroup['Media']:
						if "volumes" in media:
							# list all the volumes of the media (looking for CIRCUITPY and such)
							for volume in media['volumes']:
								device['volumes'].append(volume)
				devices += [device]
			return devices
	
		devicesInfo = readSysProfile(system_profile['SPUSBDataType'],[])
	
		# list the existing ports
		remainingPorts = list(filter(lambda x: x.vid != None, serial.tools.list_ports.comports()))

		# list the micro:bit virtual drives (that are somehow not in system_profiler)
		bitsList = findMicroBits()
	
		# loop through the devices to extract some useful data then handle the good ones
		deviceList = []
		for dev in devicesInfo:
			# vid is required
			if 'vendor_id' not in dev:
				continue
			try:
				vid = int(dev['vendor_id'].split(" ")[0],16)
			except:
				continue
			# product id
			try:
				pid = int(dev['product_id'].split(" ")[0],16)
			except:
				pid = 0
			# serial number is not always present
			if not 'serial_num' in dev:
				dev['serial_num'] = ""
			SN = dev['serial_num']
			# try to guess the port using the Location ID or Serial Number
			ttys = []
			for x in range(len(remainingPorts)):
				port = remainingPorts[x]
				if port.vid == vid and port.pid == pid \
					and port.serial_number == SN:
					ttys.append(port.device)
					remainingPorts[x] = None
			remainingPorts = list(filter(lambda x:  x is not None, remainingPorts))
			dev['ports'] = ttys
			#
			# now we select all the ones with a known VID or with an existing tty
			# (or skip the others if you will) as soon as possible
			#
			isABoard = any([dev['vendor_id'].find(x)>=0 for x in VIDS]) or len(dev['ports'])>0
			if not isABoard:
				continue
			#
			# manufacturer is kind of a mess sometimes
			if not 'manufacturer' in dev:
				dev['manufacturer'] = ""
			# identify and add the micro:bit volumes
			if dev['name'].find("micro:bit"):
				if dev['serial_num'] in bitsList:
					bitvolume = {
						'mount_point': bitsList[dev['serial_num']]
					}
					dev['volumes'].append(bitvolume)
			# list the volume(s) and the circtuipython run files
			for volume in dev['volumes']:
				if 'mount_point' in volume:
					mount = volume['mount_point']
					if mount != "":
						volume['mains'] = []
						for mainFile in mainNames:
							if os.path.exists(os.path.join(mount,mainFile)):
								volume['mains'] += [mainFile]
			# add the device to the list
			deviceList.append(dev)
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
			curDevice['volumes'] = []
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
						curDevice['volumes'].append({
							'mount_point': volume,
							'mains': mains,
						})
			#
			# go through parents and find "devpath", remove matching parents
			def noParent(dev):
				for papa in device.traverse():
					if dev['devpath'] == papa.get('DEVPATH'):
						return False
				return True
			deviceList = list(filter(noParent,deviceList))
			#
			if vid not in VIDS and len(ttys) == 0: continue
			#
			curDevice['devpath'] = devpath
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
	deviceList,remainingPorts = getDeviceList()
	print(deviceList)
	print(remainingPorts)
