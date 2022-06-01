#!/usr/bin/env python3

import click
from click_aliases import ClickAliasedGroup
from json import dumps
import os
import re
import shutil
import subprocess
import sys
import time
from . import usbinfos
from .usbinfos import port_is_repl, port_is_data


DEFAULT_WINDOWS_SERIAL_TOOLS = {
	"ttermpro": "ttermpro.exe /C={portnum}",
	"putty": "putty -sercfg 115200 -serial {port}",
}
"""List of serial tool configurations to try on windows"""
DEFAULT_UNIX_SERIAL_TOOLS = {
	"tio": "tio -b 115200 {port}",
	"screen": "screen {port} 115200",
}
"""List of serial tool configurations to try on unix systems"""
conf = {
	# command line to connect to the REPL (screen, tio)
	"SERIALTOOL" : "",
	# command line to call circup
	"CIRCUP" : "circup",
	# disable colors
	"NOCOLOR" : False,
	# separation line length
	"LINE_LENGTH" : 0,
}
"""Global configuration of the app, will be updated with env and configs"""


# click.echo/secho
def echo(*text,nl=True,**kargs):
	if bool(conf['NOCOLOR']):
		click.echo(" ".join(text), nl=nl)
	else:
		click.secho(" ".join(text), nl=nl, **kargs)


# setup the command line configuration and tools
def setup_command_tools():
	# command line conf
	try:
		conf['LINE_LENGTH'] = int(subprocess.check_output(["tput","cols"]))-1
		# not sure what exceptions are raised when that fails
	except Exception:
		pass

	# select candidates by platform
	if "win32" in sys.platform:
		default_serial_tools = DEFAULT_WINDOWS_SERIAL_TOOLS
	else:
		default_serial_tools = DEFAULT_UNIX_SERIAL_TOOLS

	# check in order the candidates
	for name, command in default_serial_tools.items():
		if shutil.which(name) is not None:
			conf['SERIALTOOL'] = command
			break

	# override configuration constants with environement variables
	for var in conf:
		environ_var = f"DISCOTOOL_{var}"
		if environ_var in os.environ:
			try:
				conf[var] = type(conf[var])(os.environ[environ_var])
			except ValueError:
				echo("Environment variable value invalid: ", nl=False)
				echo(f"{environ_var}={os.environ[environ_var]}", underline=True)


# print the text from main
def displayTheBoardsList(bList, ports=[]):
	if len(bList) == 0 and len(ports) == 0:
		echo("No device found.",fg="magenta")
		return
	for dev in bList:
		# display the device name
		echo(f"- {dev['name']} ".ljust(conf['LINE_LENGTH'],"-"), fg="yellow", bold=True)
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
			if port_is_repl(iface):
				iface = "REPL"
			elif port_is_data(iface):
				iface = "DATA"
			click.echo(f"\t{portInfo['dev']} ({iface})")
		# volumes and main files
		dev_vols = sorted(
			dev['volumes'],
			key = lambda port: port['mount_point'].lower(),
		)
		for volume in dev_vols:
			if 'mount_point' in volume:
				click.echo("\t"+volume['mount_point'],nl=False)
				if volume['name'] not in volume['mount_point']:
					click.echo(' "'+volume['name']+'"', nl=False)
				for main in volume['mains']:
					click.echo(" ("+main+")",nl=False)
				if dev['version']:
					click.echo(" v"+dev['version'],nl=False)
				click.echo("")
	# remaining serial ports not accounted for
	if len(ports) > 0:
		echo("-- Unknown Serial Ports ".ljust(conf['LINE_LENGTH'],"-"), bold=True)
		echo(" ".join(ports))


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
				if 'name' in volume \
					and volume['name'].lower().find(mount) >= 0:
					if device not in selectedDevices:
						selectedDevices.append(device)
	return selectedDevices


# remove macOS ._ files from a drive (or directory)
def tree_clean(root, force=False):
	for target in os.listdir(root):
		file = os.path.join(root,target)
		if os.path.isdir(file):
			tree_clean(file, force)
		else:
			if os.path.basename(file).startswith("._"):
				if force:
					click.echo(f"Delete {file}")
					os.remove(file)
				elif click.confirm(f"Delete {file} ?"):
					os.remove(file)


# connect to port
def connect_to_port(device, port):
	device_name = device['name']
	if "{port}" in conf['SERIALTOOL'] or "{portnum}" in conf['SERIALTOOL']:
		portnum = re.sub("[^0-9]", "", port)
		command = conf['SERIALTOOL'].format(port=port, portnum=portnum)
	else:
		command = conf['SERIALTOOL'] + " " + port
	echo(f"- Connecting to {device_name} ".ljust(conf['LINE_LENGTH'],"-"), fg="cyan", bold=True)
	echo("> "+command, fg="cyan", bold=True)
	subprocess.run(command, shell=True)


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
@click.option(
	"--color",
	is_flag=True, help="Enable colors in the terminal. Overrides the env variable DISCOTOOL_NOCOLOR to force colors."
)
@click.option(
	"--serialtool",
	default="",
	help="Command to call to access the REPL, overrides the default, and the DISCOTOOL_SERIALTOOL env variable. Default: screen or putty.exe."
)
@click.option(
	"--circuptool",
	default="",
	help="Command to call circup, overrides the default and the DISCOTOOL_CIRCUP env variable. Default is just circup."
)
@click.option(
	"--info", "-i",
	is_flag=True,
	help="Fetch more information. Can cause drive access and code reload on Circuitpython."
)
@click.pass_context
def main(ctx, auto, wait, name, serial, mount, nocolor, color, serialtool, circuptool, info):
	"""
	discotool, the discovery tool for USB microcontroller boards.
	"""
	ctx.ensure_object(dict)
	# setup the command tools configuration
	setup_command_tools()
	# skip all
	if ctx.invoked_subcommand == "version":
		return
	# overrides
	if serialtool:
		conf['SERIALTOOL'] = serialtool
	if circuptool:
		conf['CIRCUP'] = circuptool
	# no colors
	if nocolor:
		conf['NOCOLOR'] = True
	if color:
		conf['NOCOLOR'] = False
	# normalize the inputs
	name = name.lower().strip()
	serial = serial.lower().strip()
	mount = mount.lower().strip()
	# differenciate "nothing found" and "nothing asked"
	noCriteria = (serial=="" and name=="" and mount=="" and not auto)
	ctx.obj["noCriteria"] = noCriteria
	# compute the data
	deviceList, remainingPorts = usbinfos.get_devices_list(drive_info=info)
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
					deviceList, remainingPorts = usbinfos.get_devices_list()
				else:
					ctx.obj["deviceList"] = deviceList
					ctx.obj["remainingPorts"] = remainingPorts
					ctx.obj["selectedDevices"] = selectedDevices
					break
			except KeyboardInterrupt:
				# exit cleanly on ctrl-C rather than print an exception
				sys.exit(0)
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
	selectedDevices = ctx.obj["selectedDevices"]
	displayTheBoardsList(selectedDevices, [])


@main.command()
@click.pass_context
def repl(ctx):
	"""
	Connect to the REPL of the selected device.
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	if conf['SERIALTOOL'].strip() == "":
		echo("repl: No serial tool available, see documentation to set one.", fg="red")
		sys.exit(1)
	if len(selectedDevices) == 0:
		echo("No device selected.", fg="magenta")
	for device in selectedDevices:
		if len(device['ports']) == 0:
			# echo(f"No serial port found ({device_name})", fg="red")
			continue
		if len(device['ports']) == 1:
			port = device['ports'][0]
		else:
			potential_ports = [pp for pp in device['ports']
				if port_is_repl(pp['iface'])]
			if len(potential_ports) == 0:
				port = device['ports'][0]
			else:
				port = potential_ports[0]
		port = port['dev']
		connect_to_port(device, port)
		echo("Leaving REPL.", fg="cyan")


@main.command()
@click.pass_context
def data(ctx):
	"""
	Connect to the DATA port of the selected device if any.
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	if conf['SERIALTOOL'].strip() == "":
		echo("repl: No serial tool available, see documentation to set one.", fg="red")
		sys.exit(1)
	if len(selectedDevices) == 0:
		echo("No device selected.", fg="magenta")
	for device in selectedDevices:
		port = device.data
		if port is None:
			echo(f"- No data port for {device['name']} ".ljust(conf['LINE_LENGTH'],"-"), fg="red", bold=True)
			continue
		connect_to_port(device, port)
		echo("Fin.", fg="cyan")


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
		echo("- EJECTING DRIVES ".ljust(conf['LINE_LENGTH'],"-"), fg="magenta", bold=True)
		for device in selectedDevices:
			if len(device['volumes']) == 0:
				echo(f"No drive found for {device['name']}.", fg="magenta")
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
	is_flag=True,
	help="Create the target directory if it does not exist."
)
@click.option(
	"--date", "-d",
	is_flag=True,
	help="Use a time stamp as subdirectory name, or add to the supplied sub dir."
)
@click.option(
	"--format", "-f",
	help="Format the backup name. {timestamp}, {device}, {drive}, {serial}"
)
@click.argument(
	"sub_dir",
	required=False,
)
@click.pass_context
def backup(ctx, backup_dir, create, date, format, sub_dir):
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
		echo("No device selected.", fg="magenta")
	else:
		echo("- BACKING UP ".ljust(conf['LINE_LENGTH'],"-"), fg="green", bold=True)
		for device in selectedDevices:
			if len(device['volumes']) == 0:
				echo(f"No drive found for {device['name']}.", fg="magenta")
			for volume in device['volumes']:
				volume_src = volume['mount_point']
				volume_bootout = os.path.join(volume_src,"boot_out.txt")
				# only backup circuitpython boards
				if os.path.exists(volume_src) and os.path.exists(volume_bootout):
					if format:
						container_name = format.format(
							drive=volume['name'],
							timestamp=time.strftime("%Y%m%d-%H%M%S"),
							device=device['name'],
							serial=device['serial_num'],
						)
						container_name = re.sub(r"[^A-Za-z0-9-]","_",container_name).strip("_")
					else:
						container_name = re.sub(r"[^A-Za-z0-9]","_",device['name']).strip("_")
						container_name += "_SN"+device['serial_num']
						container_name += "_"+volume['name']
					container = os.path.join(targetDir, container_name)
					click.echo(f"Backing up {volume_src} to\n{container}")
					shutil.copytree(volume_src, container) # dirs_exist_ok = True
				else:
					echo(f"{volume_src} is not a circuitpython board !", fg="red")


@main.command(aliases=['cu'], context_settings={"ignore_unknown_options":True})
@click.argument("circup_options", nargs=-1)
@click.pass_context
def circup(ctx, circup_options):
	"""
	Call circup on the selected device with the given options.
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	if len(selectedDevices) == 0:
		echo("No device selected.", fg="magenta")
		return
	for device in selectedDevices:
		device_name = device['name']
		if len(device['volumes']) == 0:
			echo(f"No drive found for {device['name']}.", fg="magenta")
		for volume in device['volumes']:
			volume_src = volume['mount_point']
			volume_bootout = os.path.join(volume_src,"boot_out.txt")
			# only circup circuitpython boards
			if os.path.exists(volume_src) and os.path.exists(volume_bootout):
				command = [conf['CIRCUP'], "--path", volume_src]
				command += [x for x in circup_options]
				echo(f"- Running circup on {device_name} ".ljust(conf['LINE_LENGTH'],"-"), fg="cyan", bold=True)
				echo("> ", bold=True, nl=False)
				click.echo(" ".join(command))
				subprocess.run(" ".join(command), shell=True)
				break


@main.command(context_settings={"ignore_unknown_options":True})
@click.argument("circup_options", nargs=-1)
@click.pass_context
def install(ctx, circup_options):
	"""
	Call circup install on the selected device with the given options.
	"""
	circup_options = ("install",) + circup_options
	ctx.invoke(circup, circup_options = circup_options)


@main.command(context_settings={"ignore_unknown_options":True})
@click.argument("circup_options", nargs=-1)
@click.pass_context
def update(ctx, circup_options):
	"""
	Call circup update on the selected device with the given options.
	"""
	circup_options = ("update",) + circup_options
	ctx.invoke(circup, circup_options = circup_options)


@main.command()
@click.option(
	"--yes", "-y", "--all", "-a",
	is_flag=True, help="Always accept deleting without asking."
)
@click.pass_context
def cleanup(ctx, yes):
	"""
	Remove unwanted files from selected drives (macOS's ._* files).
	"""
	selectedDevices = ctx.obj["selectedDevices"]
	if len(selectedDevices) == 0:
		echo("No device selected.", fg="magenta")
	else:
		echo("- CLEANING FILES ".ljust(conf['LINE_LENGTH'],"-"), fg="green", bold=True)
		for device in selectedDevices:
			if len(device['volumes']) == 0:
				echo(f"No drive found for {device['name']}.", fg="magenta")
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
				except click.exceptions.Abort:
					return
				except Exception as ex:
					if yes:
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
	'repl' is the serial port identified as Circuitpython REPL (also 'console')
	'data' is the serial port identified as Circuitpython CDC2 (also 'cdc2')
	
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
				device['ports'].sort(key = lambda port: port['dev'])
				if len(device['ports']) > 0:
					values.append(device['ports'][0]['dev'])
		elif key in ("repl", "console"):
			if 'ports' in device:
				device['ports'].sort(key = lambda port: port['dev'])
				values += [pp['dev'] for pp in device['ports']
					if port_is_repl(pp['iface'])]
		elif key in ("cdc2", "data"):
			if 'ports' in device:
				device['ports'].sort(key = lambda port: port['dev'])
				values += [pp['dev'] for pp in device['ports']
					if port_is_data(pp['iface'])]
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


@main.command()
def version():
	"""
	Print the version information and number.
	"""
	from . import __version__
	print(f"Discovery tool for microcontrollers, version {__version__}")
