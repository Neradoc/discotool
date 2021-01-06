#!/usr/bin/env python3

import os, glob, json, time, sys
import subprocess, shutil, re, errno
import usbinfos

# my usual color print copy and pasted stuff

RED    = '\033[91m'
GREEN  = '\033[92m'
YELLOW = '\033[93m'
BLUE   = '\033[94m'
PURPLE = '\033[95m'
CYAN   = '\033[96m'
ENDC   = '\033[0m'
BOLD   = '\033[1m'
UNDERLINE  = '\033[4m'
FONDGRIS   = '\033[47m'
NOIRSURGRIS= '\033[7;40;39m'
BLUEONWHITE= '\033[7;44;39m'

# command line to connect to the REPL (screen,tio)
SCREEN_COMMAND = ["screen"]
# command line to call circup
CIRCUP_COMMAND = ["circup"]

# override configuration constants with config.py
if os.path.exists("config.py"):
	from config import *

# print the text from main
def displayTheText(list,ports=[]):
	outText = ""
	for dev in list:
		# display the device name
		outText += (YELLOW+BOLD+"- "+dev['name']+" "+"-" * (70 - len(dev['name']))+ENDC+"\n")
		# display tha manufacturer and serial number
		if dev['manufacturer'] != "":
			outText += ("\t"+dev['manufacturer'])
			if dev['serial_num'] != "":
				outText += (" [SN:"+dev['serial_num']+"]\n")
			else:
				outText += ("\n")
		else:
			outText += ("\t[SN:"+dev['serial_num']+"]\n")
		# print the serial ports
		for path in dev['ports']:
			outText += ("\t"+path+"\n")
		# print the volumes and main files
		for volume in dev['volumes']:
			if 'mount_point' in volume:
				outText += ("\t"+volume['mount_point'])
				for main in volume['mains']:
					outText += (" ("+main+")")
				if dev['version']:
					outText += " v"+dev['version']
				outText += ("\n")
	print(outText.rstrip())
	# print remaining tty ports not accounted for
	if len(ports) > 0:
		print(BOLD+"--","Unknown Serial Ports","-"*50,ENDC)
		print(" ".join(ports))

# interpret the arguments and run whatever needs to be run
def run_command_selector(deviceList,args):
	# normalize the inputs
	name = args.name.lower().strip()
	sn = args.sn.lower().strip()
	mount = args.mount.lower().strip()
	auto = args.auto
	eject = args.eject
	backup = args.backup
	# differenciate "nothing found" and "nothing asked"
	if sn=="" and name=="" and mount=="" and not auto:
		noCriteria = True
	else:
		noCriteria = False
	#
	# Part 1: selecting devices (or not)
	#
	selectedDevices = []
	# only one device and "--auto", connect to it
	if auto and len(deviceList) == 1:
		selectedDevices.append(deviceList[0])
	# device selected by its name (first one found that matches)
	if name != "":
		for device in deviceList:
			device_name = device['name'].lower()
			if device_name.find(name) >= 0:
				selectedDevices.append(device)
	# device selected by its serial number (first one found that matches)
	if sn != "":
		for device in deviceList:
			serial_number = device['serial_num'].lower()
			if serial_number.find(sn) >= 0:
				selectedDevices.append(device)
	# device selected by its drive path (first one that matches)
	if mount != "":
		for device in deviceList:
			for volume in device['volumes']:
				if 'mount_point' in volume \
					and volume['mount_point'].lower().find(mount) >= 0:
					selectedDevices.append(device)
	#
	# Part 2: doing something
	#
	print(args.circup)
	# backup the selection of devices found, everything if no criteria
	# NOTE: runs before circup
	if backup != None:
		print(GREEN+BOLD+"- BACKING UP "+"-"*60+ENDC)
		if noCriteria:
			selectedDevices = deviceList
		for device in selectedDevices:
			for volume in device['volumes']:
				volume_src = volume['mount_point']
				if os.path.exists(volume_src):
					container_name = re.sub(r"[^A-Za-z0-9]","_",device['name']).strip("_")
					container_name += "_SN"+device['serial_num']
					container = os.path.join(backup,container_name)
					print("Backing up",volume_src,"to\n",container)
					shutil.copytree(volume_src,container,dirs_exist_ok = True)
	# run circup with the provided argument list
	if args.circup:
		for device in selectedDevices:
			for volume in device['volumes']:
				volume_src = volume['mount_point']
				if os.path.exists(volume_src):
					command = CIRCUP_COMMAND+["--path",volume_src]
					command += re.split(" +",args.circup[0])
					print(CYAN+BOLD+"- Running circup on",name,"-"*(56-len(device['name']))+ENDC)
					print(BOLD+"> "+ENDC+" ".join(command))
					subprocess.call(command)
					break
	# connect to the REPL by default
	if backup == None and args.circup == None:
		for device in selectedDevices:
			port = device['ports'][0]
			name = device['name']
			command = SCREEN_COMMAND + [port]
			print(CYAN+BOLD+"- Connecting to",name,"-"*(56-len(name))+ENDC)
			print(BOLD+"> "+ENDC+" ".join(command))
			print(CYAN+" "+" ↓ "*24+ENDC)
			subprocess.call(command)
			print("Fin.")
			break
	# eject the selection of devices found, everything if no criteria
	if eject:
		print(PURPLE+BOLD+"- EJECTING DRIVES "+"-"*55+ENDC)
		if noCriteria:
			selectedDevices = deviceList
		for device in selectedDevices:
			for volume in device['volumes']:
				volumeName = os.path.basename(volume['mount_point'])
				command = ["osascript", "-e", "tell application \"Finder\" to eject \"{}\"".format(volumeName)]
				print("Ejection de "+volumeName)
				subprocess.call(command)
	# nothing found, or nothing to do
	return selectedDevices

def main():
	import argparse, subprocess
	parser = argparse.ArgumentParser()
	parser.add_argument('--name','-n',help="Device name to select",default="")
	parser.add_argument('--sn','-s',help="Device serial number to select",default="")
	parser.add_argument('--mount','-m',help="Mount path used by the device to select",default="")
	parser.add_argument('--auto','-a',help="Open the device if there's only one",action='store_true')
	parser.add_argument('--wait','-w',help="Keep scanning until a device matches",action='store_true')
	parser.add_argument('--eject','-e',help="Eject the disk volume(s) from the matching device",action='store_true')
	parser.add_argument('--backup','-b',help="Backup copy of all Circuipython drives found into the given directory",default=None)
	parser.add_argument('--circup','-c',help="Call circup on the selected board with the rest of the options",nargs=1)
	args = parser.parse_args()
	
	wait = args.wait
	# exit now if the backup directory does not exist
	if args.backup != None and not os.path.exists(args.backup):
		print(RED+BOLD+os.strerror(errno.ENOENT)+": "+args.backup+ENDC)
		exit(errno.ENOENT)
	
	# compute the data
	deviceList,remainingPorts = usbinfos.getDeviceList()
	# print the reminder
	print(BLUEONWHITE+BOLD+" -n name -s serial number -m mount volume -a auto "+ENDC+"\n"+BLUEONWHITE+BOLD+" -b backup -w wait -e eject -c \"circup arguments\" "+ENDC)
	# print the text
	displayTheText(deviceList,remainingPorts)
	
	# run the commands (wait)
	if wait:
		print("Wait until the device is available")
		while True:
			# try finding a device and doing something with it
			ret = run_command_selector(deviceList,args)
			# mark time
			if len(ret) == 0:
				print(".",end="")
				sys.stdout.flush()
				# loop slowly
				time.sleep(1)
				# re scan the device
				deviceList,remainingPorts = usbinfos.getDeviceList()
			else:
				break
	else:
		# run the commands once
		ret = run_command_selector(deviceList,args)
		if len(ret) == 0:
			print(PURPLE+"No device selected"+ENDC)

if __name__ == "__main__":
	main()
