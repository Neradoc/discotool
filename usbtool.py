#!/usr/bin/env python3

import os, time, sys, re
import subprocess, shutil, click
import usbinfos

# my usual color print copy and pasted stuff
# (for the mac terminal)
RED    = '\033[91m'
GREEN  = '\033[92m'
YELLOW = '\033[93m'
BLUE   = '\033[94m'
PURPLE = '\033[95m'
CYAN   = '\033[96m'
GREY   = '\033[2;40;39m'
ENDC   = '\033[0m'
BOLD   = '\033[1m'
UNDERLINE  = '\033[4m'
FONDGRIS   = '\033[47m'
NOIRSURGRIS= '\033[7;40;39m'
BLUEONWHITE= '\033[7;44;39m'

# command line to connect to the REPL (screen, tio)
SCREEN_COMMAND = ["screen"]
# command line to call circup
CIRCUP_COMMAND = ["circup"]

# override configuration constants with config.py
if os.path.exists("config.py"):
	from config import *

# print the text from main
def displayTheBoardsList(bList, ports=[]):
	outText = ""
	for dev in bList:
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
	click.echo(outText.rstrip())
	# print remaining tty ports not accounted for
	if len(ports) > 0:
		click.echo(BOLD+"--"+" Unknown Serial Ports "+"-"*50+ENDC)
		click.echo(" ".join(ports))

# interpret the arguments and select devices based on that
def find_the_devices(deviceList, auto, wait, name, serial, mount):
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
	if serial != "":
		for device in deviceList:
			serial_number = device['serial_num'].lower()
			if serial_number.find(serial) >= 0:
				selectedDevices.append(device)
	# device selected by its drive path (first one that matches)
	if mount != "":
		for device in deviceList:
			for volume in device['volumes']:
				if 'mount_point' in volume \
					and volume['mount_point'].lower().find(mount) >= 0:
					selectedDevices.append(device)
	return selectedDevices

@click.group(invoke_without_command=True)
@click.option(
	"--auto", "-a",
	is_flag=True, help="Pick the first board found for commands."
)
@click.option(
	"--wait", "-w",
	is_flag=True, help="Scan the boards until one match is found. Warning: does not wait for the board's drive to be mounted."
)
@click.option(
	"--name", "-n",
	default="",
	help="Select a device by searching in its name field.",
)
@click.option(
	"--serial", "-s",
	default="",
	help="Select a device by searching in its serial number.",
)
@click.option(
	"--mount", "-m",
	default="",
	help="Select a device by matching the path to its associated mount.",
)
@click.pass_context
def main(ctx, auto, wait, name, serial, mount):
	ctx.ensure_object(dict)
	# normalize the inputs
	name = name.lower().strip()
	serial = serial.lower().strip()
	mount = mount.lower().strip()
	# differenciate "nothing found" and "nothing asked"
	noCriteria = (serial=="" and name=="" and mount=="" and not auto)
	ctx.obj["noCriteria"] = noCriteria
	# compute the data
	deviceList, remainingPorts = usbinfos.getDeviceList()
	# print the reminder
	click.echo(GREY+"Filters: --name --serial --mount --auto --wait "+ENDC+"\n"+GREY+"Commands: list, repl, eject, backup <to_dir>, circup <options> "+ENDC)
	#
	# wait until the device pops up
	if wait:
		click.echo("Wait until the device is available")
		while True:
			try:
			# try finding a device
				if noCriteria:
					selectedDevices = deviceList
				else:
					selectedDevices = find_the_devices(deviceList, auto, wait, name, serial, mount)
				if len(selectedDevices) == 0:
					click.echo(".",nl=False)
					sys.stdout.flush()
					# loop slowly
					time.sleep(1)
					# re scan the device
					deviceList, remainingPorts = usbinfos.getDeviceList()
				else:
					ctx.obj["deviceList"] = deviceList
					ctx.obj["remainingPorts"] = remainingPorts
					ctx.obj["selectedDevices"] = selectedDevices
					break
			except KeyboardInterrupt:
				exit(0)
	else:
		# find only once
		if noCriteria:
			selectedDevices = deviceList
		else:
			selectedDevices = find_the_devices(deviceList, auto, wait, name, serial, mount)
		ctx.obj["deviceList"] = deviceList
		ctx.obj["remainingPorts"] = remainingPorts
		ctx.obj["selectedDevices"] = selectedDevices
	# here we exit and run the command, or if no command, go to repl
	if ctx.invoked_subcommand is None:
		if noCriteria:
			ctx.invoke(list)
		else:
			ctx.invoke(repl)

@main.command()
@click.pass_context
def list(ctx):
	"""
	List all the boards that have been detected
	"""
	deviceList = ctx.obj["deviceList"]
	remainingPorts = ctx.obj["remainingPorts"]
	displayTheBoardsList(deviceList, remainingPorts)

@main.command()
@click.pass_context
def repl(ctx):
	"""
	Connect to the REPL of the selected board
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	for device in selectedDevices:
		port = device['ports'][0]
		name = device['name']
		command = SCREEN_COMMAND + [port]
		click.echo(CYAN+BOLD+"- Connecting to "+name+" "+"-"*(56-len(name))+ENDC)
		click.echo(BOLD+"> "+ENDC+" ".join(command))
		click.echo(CYAN+" "+" ↓ "*24+ENDC)
		subprocess.call(command)
		click.echo("Fin.")


@main.command()
@click.pass_context
def eject(ctx):
	"""
	Eject the disk volume(s) from the matching device
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	if len(selectedDevices) == 0:
		click.echo(PURPLE+"No device selected"+ENDC)
	else:
		click.echo(PURPLE+BOLD+"- EJECTING DRIVES "+"-"*55+ENDC)
		for device in selectedDevices:
			for volume in device['volumes']:
				volumeName = os.path.basename(volume['mount_point'])
				command = ["osascript", "-e", "tell application \"Finder\" to eject \"{}\"".format(volumeName)]
				click.echo("Ejection de "+volumeName)
				subprocess.call(command)
	
@main.command()
@click.argument(
	"backup_dir",
	type=click.Path(exists=True, file_okay=False),
)
@click.argument(
	"sub_dir",
	required=False,
)
@click.pass_context
def backup(ctx, backup_dir, sub_dir):
	"""
	Backup copy of all (Circuipython) drives found into the given directory
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	if sub_dir:
		sub_dir = sub_dir.replace("/","")
		targetDir = os.path.join(backup_dir, sub_dir)
		if not os.path.exists(targetDir):
			os.mkdir(targetDir)
	else:
		targetDir = backup_dir
	if len(selectedDevices) == 0:
		click.echo(PURPLE+"No device selected"+ENDC)
	else:
		click.echo(GREEN+BOLD+"- BACKING UP "+"-"*60+ENDC)
		for device in selectedDevices:
			for volume in device['volumes']:
				volume_src = volume['mount_point']
				if os.path.exists(volume_src):
					container_name = re.sub(r"[^A-Za-z0-9]","_",device['name']).strip("_")
					container_name += "_SN"+device['serial_num']
					container = os.path.join(targetDir, container_name)
					click.echo("Backing up "+volume_src+" to\n "+container)
					shutil.copytree(volume_src, container, dirs_exist_ok = True)

@main.command()
@click.argument("circup_options", nargs=-1)
@click.pass_context
def circup(ctx, circup_options):
	"""
	Call circup on the selected board with the given options
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	for device in selectedDevices:
		name = device['name']
		for volume in device['volumes']:
			volume_src = volume['mount_point']
			if os.path.exists(volume_src):
				command = CIRCUP_COMMAND+["--path", volume_src]
				command += [x for x in circup_options]
				click.echo(CYAN+BOLD+"- Running circup on "+name+" "+"-"*(56-len(device['name']))+ENDC)
				click.echo(BOLD+"> "+ENDC+" ".join(command))
				subprocess.call(command)
				break

@main.command()
@click.argument("circup_options", nargs=-1)
@click.pass_context
def cu(ctx, circup_options):
	"""
	Alias to circup
	"""
	ctx.invoke(circup, circup_options=circup_options)

# Allows execution via `python -m circup ...`
if __name__ == "__main__":
	main()
