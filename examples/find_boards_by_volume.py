"""
A demo host-side script that
- finds a board by volume name
- sends some data to the board's data serial port

python3 find_boards_by_volume.py --mount QTPY2040 ---data "Hi there"
"""
import argparse
import discotool
import os
import serial

BOARD_DRIVE_NAME = "CIRCUITPY"
DATA_STRING = "Hello World"

# This lets you specify the drive name and data to send in the command line
parser = argparse.ArgumentParser()
parser.add_argument("--mount", type=str, help="Drive name", default=BOARD_DRIVE_NAME)
parser.add_argument("--data", type=str, help="Data to send", default=DATA_STRING)
args = parser.parse_args()

# prepare the parameters
mount_name = os.path.basename(args.mount)
data_string = args.data.encode("utf8")

# find all the devices
devs = discotool.get_identified_devices()

# and now drill into it to the the correct one
for dev in devs:
    volume = dev.volume_name
    data_port = dev.data
    print(f"{volume}")
    if volume == mount_name:
        if not dev.data:
            print("   Has no data port, trying REPL")
            data_port = dev.repl
        print(f"   Send {data_string} to {data_port}")
        with serial.Serial(data_port) as pp:
            pp.write(data_string)
    else:
        print(f"   Ignored")
