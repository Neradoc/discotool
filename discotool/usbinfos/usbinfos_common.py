import os

# Vendor IDs recognized as Arduino / Circuitpython boards
VIDS = [
	0x0483, # STM32 BOOTLOADER PID : 57105
	0x239a, # Adafruit
	0x10c4, # serial to USB ?
	0x0d28, # micro:bit
	0x2341, # Arduino
	0x1209, # https://pid.codes/
	0x303a, # Espressif https://github.com/espressif/usb-pids
]

mainNames = ["code.txt","code.py","main.py","main.txt"]

# list the drive info for a circuipython drive (code or main and version)
def get_cp_drive_info(mount):
	mains = []
	for mainFile in mainNames:
		if os.path.exists(os.path.join(mount,mainFile)):
			mains += [mainFile]
	boot_out = os.path.join(mount, "boot_out.txt")
	try:
		with open(boot_out) as boot:
			circuit_python, _ = boot.read().split(";")
			version = circuit_python.split(" ")[-3]
	except (FileNotFoundError,ValueError,IndexError):
		version = ""
	return (mains,version)
