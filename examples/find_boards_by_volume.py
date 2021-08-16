"""
A demo host-side script that
- finds a board by volume name
- sends some data to the board's data serial port

python3 find_boards_by_volume.py -m CIRCUITPY -d "Hi there"
"""
import argparse
import discotool
import os
import serial

BOARD_DRIVE_NAME = "QTPY2040"
DATA_STRING = "Hello World"

parser = argparse.ArgumentParser()
parser.add_argument(
    "--mount",
    "-m",
    type=str,
    help="Name of the board's mount",
    default=BOARD_DRIVE_NAME,
)
parser.add_argument(
    "--data",
    "-d",
    type=str,
    help="The data string to send",
    default=DATA_STRING,
)
args = parser.parse_args()

mount_name = os.path.basename(args.mount)
data_string = args.data.encode("utf8")

devs = discotool.get_identified_devices()
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
