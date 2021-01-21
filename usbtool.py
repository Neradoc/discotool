#!/usr/bin/env python3

import os, time, sys, re
import subprocess, shutil, click
from json import dumps
import usbinfos

# my usual color print copy and pasted stuff
# (for the mac terminal)
class TCMacOS: # terminal colors
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

class TCNone: # terminal colors
	RED    = ''
	GREEN  = ''
	YELLOW = ''
	BLUE   = ''
	PURPLE = ''
	CYAN   = ''
	GREY   = ''
	ENDC   = ''
	BOLD   = ''
	UNDERLINE  = ''
	FONDGRIS   = ''
	NOIRSURGRIS= ''
	BLUEONWHITE= ''

# switch on sys.platform
TC = TCMacOS()

# command line to connect to the REPL (screen, tio)
SCREEN_COMMAND = ["screen"]
# command line to call circup
CIRCUP_COMMAND = ["circup"]

# override configuration constants with config.py
try:
	from config import *
except:
	pass

# print the reminder
def showReminder():
	click.echo(TC.GREY+"Filters: --name --serial --mount --auto --wait "+TC.ENDC+"\n"+TC.GREY+"Commands: list, repl, eject, backup <to_dir>, circup <options> "+TC.ENDC)

# print the text from main
def displayTheBoardsList(bList, ports=[]):
	if len(bList) == 0 and len(ports) == 0:
		click.echo(TC.PURPLE+"No device found."+TC.ENDC)
		return
	for dev in bList:
		# display the device name
		click.echo(TC.YELLOW+TC.BOLD+"- "+dev['name']+" "+"-" * (70 - len(dev['name']))+TC.ENDC)
		# display tha manufacturer and serial number
		if dev['manufacturer'] != "":
			click.echo("\t"+dev['manufacturer'],nl=False)
			if dev['serial_num'] != "":
				click.echo(" [SN:"+dev['serial_num']+"]")
			else:
				click.echo()
		else:
			click.echo("\t[SN:"+dev['serial_num']+"]")
		# serial ports
		for path in dev['ports']:
			click.echo("\t"+path)
		# volumes and main files
		for volume in dev['volumes']:
			if 'mount_point' in volume:
				click.echo("\t"+volume['mount_point'],nl=False)
				for main in volume['mains']:
					click.echo(" ("+main+")",nl=False)
				if dev['version']:
					click.echo(" v"+dev['version'],nl=False)
				click.echo("")
	# remaining serial ports not accounted for
	if len(ports) > 0:
		click.echo(TC.BOLD+"--"+" Unknown Serial Ports "+"-"*50+TC.ENDC)
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
				if device not in selectedDevices:
					selectedDevices.append(device)
	# device selected by its serial number (first one found that matches)
	if serial != "":
		for device in deviceList:
			serial_number = device['serial_num'].lower()
			if serial_number.find(serial) >= 0:
				if device not in selectedDevices:
					selectedDevices.append(device)
	# device selected by its drive path (first one that matches)
	if mount != "":
		for device in deviceList:
			for volume in device['volumes']:
				if 'mount_point' in volume \
					and volume['mount_point'].lower().find(mount) >= 0:
					if device not in selectedDevices:
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
@click.option(
	"--nocolor",
	is_flag=True, help="Disable colors in the terminal."
)
@click.pass_context
def main(ctx, auto, wait, name, serial, mount, nocolor):
	ctx.ensure_object(dict)
	# no colors
	if nocolor or 'DISCOTOOL_NOCOLOR' in os.environ:
		global TC
		TC = TCNone()
	# normalize the inputs
	name = name.lower().strip()
	serial = serial.lower().strip()
	mount = mount.lower().strip()
	# differenciate "nothing found" and "nothing asked"
	noCriteria = (serial=="" and name=="" and mount=="" and not auto)
	ctx.obj["noCriteria"] = noCriteria
	# compute the data
	deviceList, remainingPorts = usbinfos.getDeviceList()
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
	List all the devices that have been detected.
	"""
	showReminder()
	deviceList = ctx.obj["deviceList"]
	remainingPorts = ctx.obj["remainingPorts"]
	displayTheBoardsList(deviceList, remainingPorts)

@main.command()
@click.pass_context
def repl(ctx):
	"""
	Connect to the REPL of the selected device.
	"""
	showReminder()
	selectedDevices = ctx.obj["selectedDevices"]
	for device in selectedDevices:
		name = device['name']
		if len(device['ports']) == 0:
			click.echo(TC.RED+f"No serial port found ({name})"+TC.ENDC)
			continue
		port = device['ports'][0]
		command = SCREEN_COMMAND + [port]
		click.echo(TC.CYAN+TC.BOLD+"- Connecting to "+name+" "+"-"*(56-len(name))+TC.ENDC)
		click.echo(TC.BOLD+"> "+TC.ENDC+" ".join(command))
		click.echo(TC.CYAN+" "+" ↓ "*24+TC.ENDC)
		subprocess.call(command)
		click.echo("Fin.")


@main.command()
@click.pass_context
def eject(ctx):
	"""
	Eject the disk volume(s) from the matching device (Mac only now).
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	if len(selectedDevices) == 0:
		click.echo(TC.PURPLE+"No device selected."+TC.ENDC)
	else:
		click.echo(TC.PURPLE+TC.BOLD+"- EJECTING DRIVES "+"-"*55+TC.ENDC)
		for device in selectedDevices:
			for volume in device['volumes']:
				volumeName = os.path.basename(volume['mount_point'])
				command = ["osascript", "-e", "tell application \"Finder\" to eject \"{}\"".format(volumeName)]
				click.echo("Ejecting: "+volumeName)
				subprocess.call(command)

@main.command()
@click.argument(
	"backup_dir",
	required=True,
	#type=click.Path(exists=True, file_okay=False),
)
@click.option(
	"--create", "-c",
	is_flag=True, help="Create the target directory if does not exist."
)
@click.option(
	"--date", "-d",
	is_flag=True, help="Create a sub directory based on a timestamp."
)
@click.argument(
	"sub_dir",
	required=False,
)
@click.pass_context
def backup(ctx, backup_dir, create, date, sub_dir):
	"""
	Backup copy of all (Circuipython) drives found.
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	if create:
		if not os.path.exists(backup_dir):
			os.mkdir(backup_dir)
	if not os.path.exists(backup_dir):
		click.echo(TC.RED+"The target backup directory path does not exist."+ENDC)
		return
	if date:
		timestamp = time.strftime("%Y%m%d-%H%M%S")
		if sub_dir: sub_dir += timestamp
		else: sub_dir = timestamp
	if sub_dir:
		sub_dir = sub_dir.replace("/","")
		targetDir = os.path.join(backup_dir, sub_dir)
		if not os.path.exists(targetDir):
			os.mkdir(targetDir)
	else:
		targetDir = backup_dir
	if len(selectedDevices) == 0:
		click.echo(TC.PURPLE+"No device selected"+TC.ENDC)
	else:
		click.echo(TC.GREEN+TC.BOLD+"- BACKING UP "+"-"*60+TC.ENDC)
		for device in selectedDevices:
			for volume in device['volumes']:
				volume_src = volume['mount_point']
				volume_bootout = os.path.join(volume_src,"boot_out.txt")
				# only circup circuitpython boards
				if os.path.exists(volume_src) and os.path.exists(volume_bootout):
					container_name = re.sub(r"[^A-Za-z0-9]","_",device['name']).strip("_")
					container_name += "_SN"+device['serial_num']
					container = os.path.join(targetDir, container_name)
					click.echo("Backing up "+volume_src+" to\n "+container)
					shutil.copytree(volume_src, container, dirs_exist_ok = True)
				else:
					click.echo(TC.RED+"Not a circuitpython board !"+TC.ENDC)

@main.command()
@click.argument("circup_options", nargs=-1)
@click.pass_context
def circup(ctx, circup_options):
	"""
	Call circup on the selected device with the given options.
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	for device in selectedDevices:
		name = device['name']
		for volume in device['volumes']:
			volume_src = volume['mount_point']
			volume_bootout = os.path.join(volume_src,"boot_out.txt")
			# only circup circuitpython boards
			if os.path.exists(volume_src) and os.path.exists(volume_bootout):
				command = CIRCUP_COMMAND+["--path", volume_src]
				command += [x for x in circup_options]
				click.echo(TC.CYAN+TC.BOLD+"- Running circup on "+name+" "+"-"*(56-len(device['name']))+TC.ENDC)
				click.echo(TC.BOLD+"> "+TC.ENDC+" ".join(command))
				subprocess.call(command)
				break

@main.command()
@click.argument("circup_options", nargs=-1)
@click.pass_context
def cu(ctx, circup_options):
	"""
	Alias to circup.
	"""
	ctx.invoke(circup, circup_options=circup_options)

@main.command()
@click.argument("key", required=True)
@click.pass_context
def get(ctx, key):
	"""
	Get value for the key sparated by a new line for each device.
	A few special keys give direct access to values:
	'volume' and 'port' select the first valid mounted drive or serial port.
	'main' or 'code.py' gives the path to the main Circuitpython file.
	'vid' and 'pid' are shortcuts for vendor_id and product_id.
	'sn' is a shortcut for serial_num.
	
	Example: screen `discotool -n clue get port`
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	values = []
	for device in selectedDevices:
		if key in device:
			if type(device[key]) == str:
				values.append(device[key])
			else:
				values.append(dumps(device[key]))
		elif key == "volume":
			if 'volumes' in device:
				if len(device['volumes']) > 0:
					values.append(device['volumes'][0]['mount_point'])
		elif key == "port":
			if 'ports' in device:
				if len(device['ports']) > 0:
					values.append(device['ports'][0])
		elif key == "vid":
			values.append(device['vendor_id'])
		elif key == "pid":
			values.append(device['product_id'])
		elif key == "sn":
			values.append(device['serial_num'])
		elif key == "main" or key == "code.py":
			if 'volumes' in device:
				if len(device['volumes']) > 0:
					if 'mains' in device['volumes'][0]:
						if len(device['volumes'][0]['mains']) > 0:
							path = os.path.join(device['volumes'][0]['mount_point'], device['volumes'][0]['mains'][0])
							values.append(path)
	click.echo("\n".join([str(x) for x in values]))

@main.command()
@click.pass_context
def json(ctx):
	"""
	Get the values as a json string.
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	click.echo(dumps(selectedDevices))

# Allows execution via `python -m circup ...`
if __name__ == "__main__":
	main()
