"""
Open a new tab in Terminal with Applescript for each device with a REPL.
Change the title of the tab to match the drive or board name.
Connect to the repl with tio.
"""
import discotool
import subprocess
import time

devicesList = discotool.get_identified_devices(drive_info=True)

for device in devicesList:
	print(device.repl, device.volume, device.name)
	if device.repl is None: continue

	if device.volume is not None:
		the_title = f"{device.volume}"
	else:
		the_title = f"{device.name}"

	commands = [
		["osascript", "-e", 'tell application "Terminal" to activate',],
		["osascript", "-e", 'tell application "System Events" to tell process "Terminal" to keystroke "t" using command down',],
		["echo", "-n", "-e", f"\033]0;{the_title}\007",],
		["osascript", "-e", f'''tell application "Terminal" to do script "tio {device.repl}" in selected tab of the front window''',],
	]

	for command in commands:
		subprocess.call(command)

	time.sleep(1)
