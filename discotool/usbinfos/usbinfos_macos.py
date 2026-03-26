#!/usr/bin/env python3

"""
We call ioreg to list USB devices as a plist, and find the serial ports by
comparing vid, pid and serial number or location_id with the information
from pyserial.

Virtual drives that don't appear by name in the ioreg tree are found
through psutil.disk_partitions() and their bsd_name.

We find the microbits volumes by matching the serial number on the volume
with the one in the USB. Otherwise the volume does not seem to be listed
in ioreg's direct children.

Previous versions used ``system_profiler -json SPUSBDataType``, but Apple
removed SPUSBDataType in macOS 26 Tahoe. The ioreg approach works on all
macOS versions (Tahoe and earlier) so it is now the sole backend.
"""

import os, sys, re
import plistlib
import subprocess
import psutil
#from serial.tools.list_ports import comports
from .pyserial_list_ports_osx import comports
from .usbinfos_common import *

# where to find serial ports named by location on macOS
# NOTE: we don't check for /dev/tty.usbmodem<serial_num>
#       because devices with serial numbers are found differently
SERIAL_PREFIXES = [
	"/dev/cu.usbmodem",
	"/dev/cu.usbserial-",
#	"/dev/cu.wchusbserial",
]
SERIAL_PATTERN_USBLOC = re.compile("/dev/[^0-9]*([0-9]+)$")


# ioreg helper
def _node_class(entry):
	"""Get the IOKit class of an ioreg node. The plist from ioreg -a uses
	IOObjectClass (not IOClass) for the class name."""
	return entry.get("IOObjectClass", entry.get("IOClass", ""))

# ioreg helper
def _ioreg_str(entry, *keys):
	"""Get the first non-empty string value from an ioreg entry for the
	given keys. Handles bytes values (which plistlib can return for Data
	fields) by decoding them. Returns "" if nothing found.
	"""
	for key in keys:
		val = entry.get(key)
		if val is None:
			continue
		if isinstance(val, bytes):
			try:
				val = val.decode("utf-8", errors="replace").rstrip("\x00")
			except Exception:
				continue
		elif not isinstance(val, str):
			val = str(val)
		if val:
			return val
	return ""

# ioreg helper
def _get_usb_data_from_ioreg():
	"""Call ioreg -r -c IOUSBHostDevice -a -l which outputs an XML plist
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

# ioreg helper
def _collect_usb_devices(entries):
	"""Recursively collect all IOUSBHostDevice nodes from the ioreg tree.
	ioreg -r -c IOUSBHostDevice returns top-level entries which may be
	hubs; the actual devices are nested inside IORegistryEntryChildren
	under hub-port nodes.  We need to walk the entire tree and collect
	every node whose IOObjectClass is IOUSBHostDevice (or AppleUSBDevice)
	and that has a non-zero idVendor.
	Returns a flat list of device entries.
	"""
	devices = []
	for entry in entries:
		obj_class = _node_class(entry)
		has_vid = entry.get("idVendor", 0) != 0
		if obj_class in ("IOUSBHostDevice", "AppleUSBDevice") and has_vid:
			devices.append(entry)
		# always recurse into children regardless of this node's class,
		# because devices sit under hub-port nodes (AppleUSB20HubPort etc.)
		for child in entry.get("IORegistryEntryChildren", []):
			devices.extend(_collect_usb_devices([child]))
	return devices

# ioreg helper
def _walk_children_for_ports_and_disks(node, serial_ports, bsd_names):
	"""Recursively walk IORegistryEntryChildren to find:
	- Serial ports: IOSerialBSDClient nodes with IOCalloutDevice
	- Disks: IOMedia nodes with a BSD Name starting with disk
	Stops recursion at nested IOUSBHostDevice nodes (those are separate
	devices that will be processed on their own).
	"""
	children = node.get("IORegistryEntryChildren", [])
	for child in children:
		obj_class = _node_class(child)
		# stop at nested USB devices — they are separate devices
		if obj_class in ("IOUSBHostDevice", "AppleUSBDevice"):
			if child.get("idVendor", 0) != 0:
				continue
		# serial port nodes
		if obj_class == "IOSerialBSDClient":
			callout = _ioreg_str(child, "IOCalloutDevice")
			dialin = _ioreg_str(child, "IODialinDevice")
			if callout or dialin:
				serial_ports.append({
					"callout": callout,
					"dialin": dialin,
				})
		# BSD disk / media nodes (IOMedia class)
		bsd_name = _ioreg_str(child, "BSD Name")
		if bsd_name and bsd_name.startswith("disk"):
			bsd_names.append(bsd_name)
		# recurse
		_walk_children_for_ports_and_disks(child, serial_ports, bsd_names)


# port-matching logic
def _match_ports_to_device(vid, pid, serial_num, location_id_str):
	"""Match serial ports from remainingPorts to a USB device using either
	VID+PID+serial or location_id prefix in the device path.
	Mutates the global remainingPorts list (removes matched ports).
	Returns a list of {'dev': ..., 'iface': ...} dicts.
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
			# location_id_str is e.g. "0x14630000"
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


# going through all the ioreg USB device entries
# extracting the important informations
# matching serial ports and listing the volumes
def _read_ioreg_devices(ioreg_entries, devices, allMounts, drive_info):
	global remainingPorts
	# flatten the tree: collect all actual USB devices including those
	# nested behind hubs, so we process each real device individually
	all_usb_devices = _collect_usb_devices(ioreg_entries)
	for entry in all_usb_devices:
		curDevice = {}
		# --- vendor / product IDs (integers in ioreg) ---
		vid = entry.get("idVendor", 0)
		if not vid:
			continue
		pid = entry.get("idProduct", 0)
		curDevice['vendor_id'] = vid
		curDevice['product_id'] = pid
		# serial number is not always present
		serial_num = _ioreg_str(entry,
			"USB Serial Number",
			"kUSBSerialNumberString",
		)
		curDevice['serial_num'] = serial_num
		# manufacturer is kind of a mess sometimes
		manufacturer = _ioreg_str(entry,
			"USB Vendor Name",
			"kUSBVendorString",
		)
		curDevice['manufacturer'] = manufacturer
		# location ID: ioreg gives an integer, convert to hex string
		# to match the format the rest of discotool expects ("0x14630000")
		raw_location = entry.get("locationID", 0)
		if isinstance(raw_location, int):
			location_id_str = hex(raw_location)
		else:
			location_id_str = str(raw_location)
		# try to guess the port using the Location ID or Serial Number
		ttys = _match_ports_to_device(vid, pid, serial_num, location_id_str)
		# also check for serial ports visible in the ioreg tree
		# (walk this device's children, but stop at nested USB devices)
		ioreg_serial_ports = []
		ioreg_bsd_names = []
		_walk_children_for_ports_and_disks(entry, ioreg_serial_ports, ioreg_bsd_names)
		# add any ioreg-discovered serial ports not already matched
		known_devs = {t['dev'] for t in ttys}
		for sp in ioreg_serial_ports:
			dev = sp.get("callout", "") or sp.get("dialin", "")
			if dev and dev not in known_devs:
				# try to find it in remainingPorts to get the interface name
				iface = ""
				for port in list(remainingPorts):
					if port.device == dev:
						iface = port.interface or ""
						remainingPorts.remove(port)
						break
				ttys.append({'dev': dev, 'iface': iface})
				known_devs.add(dev)
		curDevice['ports'] = ttys
		#
		# now we select all the ones with a known VID or with an existing tty
		# (or skip the others if you will) as soon as possible
		#
		if not (vid in VIDS or len(ttys) > 0):
			continue
		# name: prefer explicit USB product name properties
		curDevice['name'] = _ioreg_str(entry,
			"USB Product Name",
			"kUSBProductString",
		)
		# list the volume(s) and the circuitpython run files
		deviceVolumes = []
		version = ""
		mains = []
		# resolve BSD names found in the ioreg tree to mount points
		for bsd_name in ioreg_bsd_names:
			disk = os.path.join("/dev", bsd_name)
			if disk in allMounts:
				mount = allMounts[disk]
				if drive_info:
					mains, version = get_cp_drive_info(mount)
				deviceVolumes.append({
					'name': os.path.basename(mount),
					'mount_point': mount,
					'mains': mains,
				})
		# also check allMounts for partitions whose parent disk matches
		# our ioreg bsd_names (e.g. ioreg shows "disk4", mount has "disk4s1")
		for bsd_name in ioreg_bsd_names:
			prefix = os.path.join("/dev", bsd_name)
			for mount_dev, mount_point in allMounts.items():
				if mount_dev.startswith(prefix) and mount_dev != prefix:
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
		devices += [curDevice]
	return devices


def get_devices_list(drive_info=False):
	global remainingPorts
	# ioreg -r -c IOUSBHostDevice -a -l
	ioreg_data = _get_usb_data_from_ioreg()

	# list the existing ports
	remainingPorts = [x for x in comports() if x.vid is not None]

	# list the mounts to match the mount points
	allMounts = {}
	for part in psutil.disk_partitions():
		allMounts[part.device] = part.mountpoint

	# list the devices
	if ioreg_data is not None:
		deviceList = _read_ioreg_devices(ioreg_data, [], allMounts, drive_info)
	else:
		deviceList = []

	rp = [port.device for port in remainingPorts]
	return (deviceList, rp)
