"""
Install a uf2 on a board that is not in bootloader mode already
"""
import argparse
import discotool
import os
import serial
import shutil
import time

PRODUCT_NAME = "QT PY"  # not case sensitive

def serial_trick(port):
    serial.Serial(port, 1200).close()

# This lets you specify the drive name and data to send in the command line
parser = argparse.ArgumentParser()
parser.add_argument("--name", type=str, help="Product name", default="")
parser.add_argument("--uf2", type=str, help="Data to send", default="firmware.uf2")
parser.add_argument("--vid", type=int, help="Product name", default=0)
args = parser.parse_args()

# prepare the parameters
product_name = args.name
uf2_file = args.uf2

if not os.path.exists(uf2_file):
    print("UF2 file not found")

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
        print("Looking for boot device")
        time.sleep(1)
        devices = discotool.get_identified_devices()
        found = False
        for device in devices:
            if device["usb_location"] == usb_port:
                board = device
                found = True
        if found:
            break
    else: # no break:
        print("Timeout: board BOOT drive not found")
        continue

    print(f"Copy {uf2_file} to {board.drive}")
    uf2_name = os.path.basename(uf2_file)
    shutil.copyfile(uf2_file, os.join(board.drive, uf2_name))