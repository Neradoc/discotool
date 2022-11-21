"""
A demo host-side script that
- finds a board by product name ("pico", "macropad", "featherS3"...)
- sends some data to the board's data serial port

python3 find_boards_with_filters.py --name FeatherS3 ---data "Hi there"
"""
import argparse
import discotool
import os
import serial

PRODUCT_NAME = "QT PY"  # not case sensitive
DATA_STRING = "Hello World"

# This lets you specify the drive name and data to send in the command line
parser = argparse.ArgumentParser()
parser.add_argument("--name", type=str, help="Product name", default="")
parser.add_argument("--data", type=str, help="Data to send", default=DATA_STRING)
parser.add_argument("--vid", type=int, help="Vendor ID", default=0)
args = parser.parse_args()

# prepare the parameters
product_name = args.name
data_string = args.data.encode("utf8")
vid = args.vid

# use filters based on given parameters
if vid != 0 and product_name == "":
    boards = discotool.devices_by_vidpid(vid)
elif not product_name:
    boards = discotool.devices_by_name(PRODUCT_NAME)
else:
    boards = discotool.devices_by_name(product_name)

# send data to whatever is found
if boards and (data_port := boards[0].data):
    print(f"Board found: {boards[0].name}")
    print(f"Send {data_string} to {data_port}")
    with serial.Serial(data_port) as pp:
        pp.write(data_string)
else:
    print(f"Could not find a {product_name} with an open data port.")
