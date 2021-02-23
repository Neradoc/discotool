#!/usr/bin/env python3

import os, time, sys, re
import subprocess, shutil, click
from json import dumps
import usbinfos
from click_aliases import ClickAliasedGroup

# command line to connect to the REPL (screen, tio)
SCREEN_COMMAND = ["screen"]
# command line to call circup
CIRCUP_COMMAND = ["circup"]
# disable colors
DISCOTOOL_NOCOLOR = False

# override configuration constants with config.py
try:
	from config import *
except:
	pass

# string description of the circuitpython REPL serial port (startswith)
SERIAL_PORT_REPL = "CircuitPython CDC "
# string description of the circuitpython secondary serial port (startswith)
SERIAL_PORT_CDC2 = "CircuitPython CDC2 "

# click.echo/secho
def echo(*text,nl=True,**kargs):
	if DISCOTOOL_NOCOLOR:
		click.echo(" ".join(text), nl=nl)
	else:
		click.secho(" ".join(text), nl=nl, **kargs)

# print the text from main
def displayTheBoardsList(bList, ports=[]):
	if len(bList) == 0 and len(ports) == 0:
		echo("No device found.",fg="magenta")
		return
	for dev in bList:
		# display the device name
		echo(f"- {dev['name']}", "-" * (70 - len(dev['name'])), fg="yellow", bold=True)
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
		dev_ports = sorted(
			dev['ports'],
			key = lambda port: port['iface'],
		)
		for portInfo in dev_ports:
			iface = portInfo['iface']
			if iface.startswith(SERIAL_PORT_REPL):
				iface = "REPL"
			elif iface.startswith(SERIAL_PORT_CDC2):
				iface = "CDC2"
			click.echo(f"\t{portInfo['dev']} ({iface})")
		# volumes and main files
		dev_vols = sorted(
			dev['volumes'],
			key = lambda port: port['mount_point'].lower(),
		)
		for volume in dev_vols:
			if 'mount_point' in volume:
				click.echo("\t"+volume['mount_point'],nl=False)
				for main in volume['mains']:
					click.echo(" ("+main+")",nl=False)
				if dev['version']:
					click.echo(" v"+dev['version'],nl=False)
				click.echo("")
	# remaining serial ports not accounted for
	if len(ports) > 0:
		echo("-- Unknown Serial Ports", "-"*50, bold=True)
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

# remove macOS ._ files from a drive (or directory)
def tree_clean(root, force=False):
	for target in os.listdir(root):
		file = os.path.join(root,target)
		if os.path.isdir(file):
			tree_clean(file)
		else:
			if os.path.basename(file).startswith("._"):
				if force or click.confirm(f"Delete {file} ?"):
					os.remove(file)

@click.group(invoke_without_command=True, cls=ClickAliasedGroup)
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
		global DISCOTOOL_NOCOLOR
		DISCOTOOL_NOCOLOR = True
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
	deviceList = ctx.obj["deviceList"]
	remainingPorts = ctx.obj["remainingPorts"]
	displayTheBoardsList(deviceList, remainingPorts)

@main.command()
@click.pass_context
def repl(ctx):
	"""
	Connect to the REPL of the selected device.
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	for device in selectedDevices:
		name = device['name']
		if len(device['ports']) == 0:
			echo(f"No serial port found ({name})", fg="red")
			continue
		if len(device['ports']) == 1:
			port = device['ports'][0]
		else:
			potential_ports = [pp for pp in device['ports']
						if pp['iface'].startswith(SERIAL_PORT_REPL)]
			if len(potential_ports) == 0:
				port = device['ports'][0]
			else:
				port = potential_ports[0]
		#
		command = SCREEN_COMMAND + [port['dev']]
		echo(f"- Connecting to {name}", "-"*(56-len(name)), fg="cyan", bold=True)
		echo("> ", bold=True, nl=False)
		click.echo(" ".join(command))
		echo(" "+" ↓ "*24, fg="cyan")
		subprocess.call(command)
		click.echo("Fin.")


@main.command()
@click.pass_context
def eject(ctx):
	"""
	Eject the disk volume(s) from the matching device (Mac only).
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	if len(selectedDevices) == 0:
		echo("No device selected.", fg="magenta")
	else:
		echo("- EJECTING DRIVES "+"-"*55, fg="magenta", bold=True)
		for device in selectedDevices:
			for volume in device['volumes']:
				if sys.platform == "darwin":
					volumeName = os.path.basename(volume['mount_point'])
					command = ["osascript", "-e", "tell application \"Finder\" to eject \"{}\"".format(volumeName)]
					click.echo("Ejecting: "+volumeName)
					subprocess.call(command)
				else:
					echo(f"Not implemented on {sys.platform}", fg="red")

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
		echo("The target backup directory path does not exist.", fg="red")
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
		echo("No device selected", fg="magenta")
	else:
		echo("- BACKING UP "+"-"*60, fg="green", bold=True)
		for device in selectedDevices:
			for volume in device['volumes']:
				volume_src = volume['mount_point']
				volume_bootout = os.path.join(volume_src,"boot_out.txt")
				# only backup circuitpython boards
				if os.path.exists(volume_src) and os.path.exists(volume_bootout):
					container_name = re.sub(r"[^A-Za-z0-9]","_",device['name']).strip("_")
					container_name += "_SN"+device['serial_num']
					container = os.path.join(targetDir, container_name)
					click.echo(f"Backing up {volume_src} to\n{container}")
					shutil.copytree(volume_src, container, dirs_exist_ok = True)
				else:
					echo(f"{volume_src} is not a circuitpython board !", fg="red")

@main.command(aliases=['cu'])
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
				echo("- Running circup on "+name+" "+"-"*(56-len(device['name'])), fg="cyan", bold=True)
				echo("> ", bold=True, nl=False)
				click.echo(" ".join(command))
				subprocess.call(command)
				break


@main.command()
@click.option(
	"--yes", "-y",
	is_flag=True, help="Always accept deleting without asking."
)
@click.pass_context
def cleanup(ctx, yes):
	"""
	Remove unwanted files from selected drives (macOS's ._* files).
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	if len(selectedDevices) == 0:
		echo("No device selected", fg="magenta")
	else:
		echo("- CLEANING FILES "+"-"*60, fg="green", bold=True)
		for device in selectedDevices:
			for volume in device['volumes']:
				try:
					volume_src = volume['mount_point']
					volume_bootout = os.path.join(volume_src,"boot_out.txt")
					# only cleanup circuitpython boards
					if os.path.exists(volume_src) and os.path.exists(volume_bootout):
						echo(f"Cleanup on drive: {volume_src}",fg="cyan")
						# erase all "._*" files
						tree_clean(volume_src, yes)
					else:
						echo(f"{volume_src} is not a circuitpython board !", fg="red")
				except Exception as ex:
					echo("An error occurred, skipping drive:", fg="red")
					echo("\t", str(ex), fg="red")


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
					values.append(device['ports'][0]['dev'])
		elif key == "repl":
			if 'ports' in device:
				values += [pp['dev'] for pp in device['ports']
					if pp['iface'].startswith(SERIAL_PORT_REPL)]
		elif key == "cdc":
			if 'ports' in device:
				values += [pp['dev'] for pp in device['ports']
					if pp['iface'].startswith(SERIAL_PORT_CDC2)]
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
@click.option(
	"--pretty", "-p",
	is_flag=True, help="Pretty print the json with 2 spaces (I know...) indent."
)
@click.pass_context
def json(ctx,pretty):
	"""
	Get the values as a json string.
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	if pretty: indent = 2
	else: indent = None
	click.echo(dumps(selectedDevices,indent=indent))

# Allows execution via `python -m circup ...`
if __name__ == "__main__":
	main()
