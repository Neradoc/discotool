#!/usr/bin/env python3

"""
We call a system command (system_profiler) to list USB devices. At least it
outputs json. We find the serial ports by comparing vid, pid and serial number
or location_id with the information from pyserial.

Virtual drives that don't appear by name in SPUSBDataType are found through
psutil.disk_partitions() and their bsd_name.

We find the microbits volumes by matching the serial number on the volume with
the one in the USB. Otherwise the volume does not seem to be listed in
system_profiler.

On macOS 26 (Tahoe) and later, SPUSBDataType was removed from system_profiler.
In that case we fall back to ``ioreg -r -c IOUSBHostDevice -a -l`` which
outputs an XML plist of the IORegistry USB device tree, and normalize the
result into the same format that readSysProfile() would have produced.
"""

import os, json, sys, re
import plistlib
import subprocess
import psutil
#from serial.tools.list_ports import comports
from .pyserial_list_ports_osx import comports
from .usbinfos_common import *

# where to find serial ports named by location on macOS
# NOTE: we don't check for /dev/tty.usbmodem<serial_num>
#	because devices with serial numbers are found differently
SERIAL_PREFIXES = [
	"/dev/cu.usbmodem",
	"/dev/cu.usbserial-",
#	"/dev/cu.wchusbserial",
]
SERIAL_PATTERN_USBLOC = re.compile("/dev/[^0-9]*([0-9]+)$")

# Backend 1 — system_profiler (macOS ≤ 15 Sequoia)

# going recursively through all the devices
# extracting the important informations
# skipping the media infos and listing the volumes
def readSysProfile(profile, devices, allMounts, drive_info):
	global remainingPorts
	for subGroup in profile:
		# go depth first
		if "_items" in subGroup:
			devices = readSysProfile(subGroup['_items'],devices,allMounts,drive_info)
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
		ttys = _match_ports_to_device(vid, pid, serial_num, subGroup.get('location_id', ''))
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
		mains = []
		if 'Media' in subGroup:
			for media in subGroup['Media']:
				if "volumes" in media:
					# list all the volumes of the media
					for volume in media['volumes']:
						if 'mount_point' in volume:
							mount = volume['mount_point']
							if drive_info:
								mains,version = get_cp_drive_info(mount)
							deviceVolumes.append({
								'name': volume['_name'],
								'mount_point': mount,
								'mains': mains,
							})
				if 'bsd_name' in media:
					disk = os.path.join("/dev",media['bsd_name'])
					if disk in allMounts:
						mount = allMounts[disk]
						if drive_info:
							mains,version = get_cp_drive_info(mount)
						deviceVolumes.append({
							'name': os.path.basename(mount),
							'mount_point': mount,
							'mains': mains,
						})
		curDevice['volumes'] = deviceVolumes
		curDevice['version'] = version
		curDevice['usb_location'] = subGroup['location_id'].split(" ")[0]
		devices += [curDevice]
	return devices

# Backend 2 — ioreg (macOS 26 Tahoe and later)

def _get_usb_data_from_ioreg():
	"""
	Call ``ioreg -r -c IOUSBHostDevice -a -l`` which outputs an XML plist
	of every IOUSBHostDevice with the full subtree of children.
	Returns the parsed plist (a list of dicts), or None on failure.
	"""
	try:
		raw = subprocess.check_output(
			["ioreg", "-r", "-c", "IOUSBHostDevice", "-a", "-l"],
			stderr=subprocess.DEVNULL,
		)
	except (subprocess.CalledProcessError, FileNotFoundError):
		return None
	if not raw or not raw.strip():
		return None
	try:
		data = plistlib.loads(raw)
	except Exception:
		return None
	if not isinstance(data, list) or not data:
		return None
	return data


def _ioreg_walk_children(node, serial_ports, bsd_names):
	"""
	Recursively walk ``IORegistryEntryChildren`` to find:
	  - Serial ports: IOSerialBSDClient nodes with IOCalloutDevice
	  - Disks: nodes with a ``BSD Name`` starting with ``disk``
	"""
	children = node.get("IORegistryEntryChildren", [])
	for child in children:
		io_class = child.get("IOClass", "")
		# serial port nodes
		if io_class == "IOSerialBSDClient":
			callout = child.get("IOCalloutDevice", "")
			dialin = child.get("IODialinDevice", "")
			if callout or dialin:
				serial_ports.append({
					"callout": callout,
					"dialin": dialin,
				})
		# BSD disk / media nodes
		bsd_name = child.get("BSD Name", "")
		if bsd_name and bsd_name.startswith("disk"):
			bsd_names.append(bsd_name)
		# recurse
		_ioreg_walk_children(child, serial_ports, bsd_names)


def readIOReg(ioreg_entries, devices, allMounts, drive_info):
	"""
	Walk the list of ioreg IOUSBHostDevice entries and build the device
	list in the same format as readSysProfile().
	"""
	global remainingPorts
	for entry in ioreg_entries:
		curDevice = {}
		# --- vendor / product IDs (integers in ioreg, not hex strings) ---
		vid = entry.get("idVendor", 0)
		if not vid:
			continue
		pid = entry.get("idProduct", 0)
		curDevice['vendor_id'] = vid
		curDevice['product_id'] = pid

		# --- serial number ---
		serial_num = (
			entry.get("USB Serial Number", "")
			or entry.get("kUSBSerialNumberString", "")
		)
		curDevice['serial_num'] = serial_num

		# --- manufacturer ---
		manufacturer = (
			entry.get("USB Vendor Name", "")
			or entry.get("kUSBVendorString", "")
		)
		curDevice['manufacturer'] = manufacturer

		# --- location ID ---
		# ioreg gives locationID as an integer; convert to hex string
		# to match the format system_profiler uses ("0x14630000")
		raw_location = entry.get("locationID", 0)
		if isinstance(raw_location, int):
			location_id_str = hex(raw_location)
		else:
			location_id_str = str(raw_location)

		# --- match serial ports (same logic as system_profiler path) ---
		ttys = _match_ports_to_device(vid, pid, serial_num, location_id_str)

		# --- also check for serial ports found inside the ioreg tree ---
		# (these are ports that ioreg can see directly as children)
		ioreg_serial_ports = []
		ioreg_bsd_names = []
		_ioreg_walk_children(entry, ioreg_serial_ports, ioreg_bsd_names)

		# Add any ioreg-discovered serial ports not already matched
		known_devs = {t['dev'] for t in ttys}
		for sp in ioreg_serial_ports:
			dev = sp.get("callout", "") or sp.get("dialin", "")
			if dev and dev not in known_devs:
				# Try to find it in remainingPorts to get the interface name
				iface = ""
				for port in list(remainingPorts):
					if port.device == dev:
						iface = port.interface or ""
						remainingPorts.remove(port)
						break
				ttys.append({'dev': dev, 'iface': iface})
				known_devs.add(dev)

		curDevice['ports'] = ttys

		# --- filter: known VID or has a serial port ---
		if not (vid in VIDS or len(ttys) > 0):
			continue

		# --- name ---
		curDevice['name'] = (
			entry.get("USB Product Name", "")
			or entry.get("kUSBProductString", "")
			or entry.get("IORegistryEntryName", "")
		)

		# --- volumes ---
		deviceVolumes = []
		version = ""
		mains = []

		# Resolve BSD names found in the ioreg tree to mount points
		for bsd_name in ioreg_bsd_names:
			# Try with and without slice suffix (disk4 vs disk4s1)
			for bsd_variant in [bsd_name, ]:
				disk = os.path.join("/dev", bsd_variant)
				if disk in allMounts:
					mount = allMounts[disk]
					if drive_info:
						mains, version = get_cp_drive_info(mount)
					deviceVolumes.append({
						'name': os.path.basename(mount),
						'mount_point': mount,
						'mains': mains,
					})

		# Also check allMounts for partitions whose parent disk matches
		# our ioreg bsd_names (e.g. ioreg shows "disk4", mount has "disk4s1")
		for bsd_name in ioreg_bsd_names:
			for mount_dev, mount_point in allMounts.items():
				# /dev/disk4s1 starts with /dev/disk4
				if mount_dev.startswith(os.path.join("/dev", bsd_name)):
					# avoid duplicates
					if not any(v['mount_point'] == mount_point for v in deviceVolumes):
						if drive_info:
							mains, version = get_cp_drive_info(mount_point)
						deviceVolumes.append({
							'name': os.path.basename(mount_point),
							'mount_point': mount_point,
							'mains': mains,
						})

		curDevice['volumes'] = deviceVolumes
		curDevice['version'] = version
		curDevice['usb_location'] = location_id_str
		devices.append(curDevice)

	return devices

# Shared port-matching logic (used by both backends)
def _match_ports_to_device(vid, pid, serial_num, location_id_str):
	"""
	Match serial ports from remainingPorts to a USB device using either
	VID+PID+serial or location_id prefix in the device path.

	Mutates the global remainingPorts list (removes matched ports).
	Returns a list of ``{'dev': ..., 'iface': ...}`` dicts.
	"""
	global remainingPorts
	ttys = []
	for port in list(remainingPorts):
		found = False
		# has SN, match it with the serial ports
		if port.vid == vid and port.pid == pid \
			and serial_num != "" and port.serial_number == serial_num:
			iface = port.interface or ""
			ttys.append({'dev':port.device,'iface':iface})
			remainingPorts.remove(port)
		# no SN, use location ID with standard mac paths
		elif serial_num == "":
			# location_id_str is e.g. "0x14630000" or "0x14630000 / 7"
			zlocation = location_id_str[2:].split()[0]
			for zpos in range(len(zlocation)):
				# remove ending zeros one by one
				location = zlocation[:len(zlocation)-zpos]
				for locationStr in SERIAL_PREFIXES:
					if port.device.startswith(locationStr+location):
						iface = port.interface or ""
						ttys.append({'dev':port.device,'iface':iface})
						remainingPorts.remove(port)
						found = True
				if not found:
					res = SERIAL_PATTERN_USBLOC.search(port.device)
					if res and res.group(1) == location:
						iface = port.interface or ""
						ttys.append({'dev':port.device,'iface':iface})
						remainingPorts.remove(port)
						found = True
				if location[-1] != "0" or found:
					break
	return ttys


def get_devices_list(drive_info=False):
	global remainingPorts

	# list the existing ports
	remainingPorts = [x for x in comports() if x.vid is not None]

	# list the mounts to match the mount points
	allMounts = {}
	for part in psutil.disk_partitions():
		allMounts[part.device] = part.mountpoint

	# --- Try system_profiler first (works on macOS ≤ 15 Sequoia) ---
	system_profile = _get_system_profiler_data()
	if system_profile is not None:
		deviceList = readSysProfile(
			system_profile['SPUSBDataType'], [], allMounts, drive_info
		)
		rp = [port.device for port in remainingPorts]
		return (deviceList, rp)

	# --- Fallback to ioreg (macOS 26 Tahoe where SPUSBDataType is gone) ---
	ioreg_data = _get_usb_data_from_ioreg()
	if ioreg_data is not None:
		deviceList = readIOReg(ioreg_data, [], allMounts, drive_info)
		rp = [port.device for port in remainingPorts]
		return (deviceList, rp)

	# --- Nothing worked ---
	rp = [port.device for port in remainingPorts]
	return ([], rp)


def _get_system_profiler_data():
	"""
	Try ``system_profiler -json SPUSBDataType``. Returns the parsed JSON
	dict on success, or None if the command fails (e.g. on Tahoe where
	SPUSBDataType no longer exists).
	"""
	try:
		ses = subprocess.check_output(
			["system_profiler", "-json", "SPUSBDataType"],
			stderr=subprocess.DEVNULL,
		)
	except (subprocess.CalledProcessError, FileNotFoundError):
		return None
	if not ses or not ses.strip():
		return None
	try:
		data = json.loads(ses)
	except (json.JSONDecodeError, ValueError):
		return None
	# system_profiler may return valid JSON but with an empty list
	if not data.get("SPUSBDataType"):
		return None
	return data
