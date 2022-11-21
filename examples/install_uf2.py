"""
Install a uf2 on a board that is not in bootloader mode already
"""
import argparse
import discotool
import os
import serial
import shutil
import time

def serial_trick(port):
    serial.Serial(port, 1200).close()

# This lets you specify the drive name and data to send in the command line
parser = argparse.ArgumentParser()
parser.add_argument("--name", type=str, help="Product name")
parser.add_argument("--uf2", type=str, help="Data to send", default="firmware.uf2")
args = parser.parse_args()

# prepare the parameters
product_name = args.name
uf2_file = args.uf2

if not os.path.exists(uf2_file):
    print("UF2 file not found, running in test mode")

# use filters based on given parameters
if not product_name:
    boards = discotool.devices_by_name(PRODUCT_NAME)
else:
    boards = discotool.devices_by_name(product_name)

# copy uf2 to board
for board in boards:
    port = board.repl
    usb_port = board["usb_location"]
    print(f"Board found: {board['name']} @ {usb_port}")
    if port:
        serial_trick(port)
    else:
        continue

    for i in range(10):
        print("Waiting for boot device with drive")
        time.sleep(1)
        devices = discotool.get_identified_devices()
        found = False
        for device in devices:
            if device["usb_location"] == usb_port:
                if device.drive is not None:
                    board = device
                    found = True
        if found:
            break
    else: # no break:
        print("Timeout: board BOOT drive not found")
        continue

    print(f"Copy {uf2_file} to {board.drive}")
    uf2_name = os.path.basename(uf2_file)
    if os.path.exists(uf2_file):
        shutil.copyfile(uf2_file, os.path.join(board.drive, uf2_name))
    else:
        print("File does not exist, no copy")
