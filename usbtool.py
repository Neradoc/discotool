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

CIRCUP_COMMAND = ["circup"]

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

# execute tio and exit
def connect_with_tio_and_exit(port,name):
	command = ["tio",port]
	print(CYAN+BOLD+"- Connecting to",name,"-"*(56-len(name))+ENDC)
	print(BOLD+"> "+ENDC+" ".join(command))
	print(CYAN+" "+" ↓ "*24+ENDC)
	subprocess.call(command)
	print("Fin.")
	exit(0)

# run tio from the commands
def run_command_and_exit(deviceList,args):
	# normalize the inputs
	name = args.name.lower()
	sn = args.sn.lower()
	mount = args.mount.lower()
	auto = args.auto
	eject = args.eject
	backup = args.backup
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
	# if no selection pick all for backup
	if len(selectedDevices)==0:
		if backup != None and sn=="" and name=="" and mount=="":
			selectedDevices = deviceList
		else:
			if sn!="" or name!="" or mount!="":
				print(PURPLE+"No device selected"+ENDC)
			return
	# do something with the found ones
	if backup != None:
		print(GREEN+BOLD+"- BACKING UP "+"-"*60+ENDC)
		for device in selectedDevices:
			for volume in device['volumes']:
				volume_src = volume['mount_point']
				boot_out = volume_src + "/boot_out.txt"
				if os.path.exists(boot_out):
					container_name = re.sub(r"[^A-Za-z0-9]","_",device['name']).strip("_")
					container_name += "_SN"+device['serial_num']
					container = os.path.join(backup,container_name)
					print("Backing up",volume_src,"to\n",container)
					shutil.copytree(volume_src,container,dirs_exist_ok = True)
	# eject the selection of devices found
	if eject:
		print(PURPLE+BOLD+"- EJECTING DRIVES "+"-"*55+ENDC)
		for device in selectedDevices:
			for volume in device['volumes']:
				volumeName = os.path.basename(volume['mount_point'])
				command = ["osascript", "-e", "tell application \"Finder\" to eject \"{}\"".format(volumeName)]
				print("Ejection de "+volumeName)
				subprocess.call(command)
	# run tio after all that
	if backup == None and not eject:
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
		else:
			for device in selectedDevices:
				connect_with_tio_and_exit(device['ports'][0],device['name'])
	# nothing found, or nothing to do

def main():
	import argparse, subprocess
	parser = argparse.ArgumentParser()
	parser.add_argument('--name','-n',help="Device name to connect to with tio",default="")
	parser.add_argument('--sn','-s',help="Device serial number to connect to",default="")
	parser.add_argument('--mount','-m',help="Mount path used by the device to connect to",default="")
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
	print(BLUEONWHITE+BOLD+" -n name -s serial number -m mount volume"
		" -a auto -b backup -w wait "+ENDC+"\n"
		+BLUEONWHITE+BOLD+" -e eject -c \"circup arguments\" "+ENDC)
	# print the text
	displayTheText(deviceList,remainingPorts)
	
	# run tio from the commands
	if wait:
		print("Wait until the device is available")
		while True:
			# try running tio
			run_command_and_exit(deviceList,args)
			# mark time
			print(".",end="")
			sys.stdout.flush()
			# loop slowly
			time.sleep(1)
			# re scan the device
			deviceList,remainingPorts = usbinfos.getDeviceList()
	else:
		# try running tio
		run_command_and_exit(deviceList,args)

if __name__ == "__main__":
	main()
