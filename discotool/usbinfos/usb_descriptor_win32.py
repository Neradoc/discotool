"""
Retrieve the USB descriptor information from connected devices
using the win32api module.

Ported to python3 and modified from:
https://stackoverflow.com/questions/24756591/python-to-get-usb-descriptor
Note the get_str_desc fix at the bottom.
"""

from __future__ import print_function
import argparse
import string
import struct
import sys

import win32api
import win32file
import pywintypes


class DeviceInfo:
    """
    Device information class
    """
    def __init__(self, vid, pid, manufacturer, product, serial_number, location):
        self.vid = vid
        self.pid = pid
        self.manufacturer = manufacturer
        self.product = product
        if serial_number == 0:
            self.serial_number = ""
        else:
            self.serial_number = str(serial_number).upper()
        self.location = ".".join(f"{i}" for i in location)

    def __repr__(self):
        return (
            "{\n"
            f"\tpid:{repr(self.vid)},\n"
            f"\tpid:{repr(self.pid)},\n"
            f"\tmanufacturer:{repr(self.manufacturer)},\n"
            f"\tproduct:{repr(self.product)},\n"
            f"\tserial_number:{repr(self.serial_number)},\n"
            f"\tlocation:{repr(self.location)},\n"
            "}"
        )


def CTL_CODE(DeviceType, Function, Method, Access):
    return (DeviceType << 16) | (Access << 14) | (Function << 2) | Method
def USB_CTL(id):
    # CTL_CODE(FILE_DEVICE_USB, (id), METHOD_BUFFERED, FILE_ANY_ACCESS)
    return CTL_CODE(0x22, id, 0, 0)

IOCTL_USB_GET_ROOT_HUB_NAME = USB_CTL(258)                   # HCD_GET_ROOT_HUB_NAME
IOCTL_USB_GET_NODE_INFORMATION = USB_CTL(258)                # USB_GET_NODE_INFORMATION
IOCTL_USB_GET_NODE_CONNECTION_INFORMATION = USB_CTL(259)     # USB_GET_NODE_CONNECTION_INFORMATION
IOCTL_USB_GET_NODE_CONNECTION_DRIVERKEY_NAME = USB_CTL(264)  # USB_GET_NODE_CONNECTION_DRIVERKEY_NAME
IOCTL_USB_GET_NODE_CONNECTION_NAME = USB_CTL(261)            # USB_GET_NODE_CONNECTION_NAME
IOCTL_USB_GET_DESCRIPTOR_FROM_NODE_CONNECTION = USB_CTL(260) # USB_GET_DESCRIPTOR_FROM_NODE_CONNECTION

USB_CONFIGURATION_DESCRIPTOR_TYPE = 2
USB_STRING_DESCRIPTOR_TYPE = 3
USB_INTERFACE_DESCRIPTOR_TYPE = 4
MAXIMUM_USB_STRING_LENGTH = 255


def open_dev(name):
    try:
        handle = win32file.CreateFile(name,
                                  win32file.GENERIC_WRITE,
                                  win32file.FILE_SHARE_WRITE,
                                  None,
                                  win32file.OPEN_EXISTING,
                                  0,
                                  None)
    except pywintypes.error as e:
        return None
    return handle


def get_root_hub_name(handle):
    buf = win32file.DeviceIoControl(handle,
                                IOCTL_USB_GET_ROOT_HUB_NAME,
                                None,
                                6,
                                None)
    act_len, _ = struct.unpack('LH', buf)
    buf = win32file.DeviceIoControl(handle,
                                IOCTL_USB_GET_ROOT_HUB_NAME,
                                None,
                                act_len,
                                None)
    return buf[4:].decode('utf-16le', "backslashreplace")


def get_driverkey_name(handle, index):
    key_name = chr(index) + '\0'*9
    try:
        buf = win32file.DeviceIoControl(handle,
                                    IOCTL_USB_GET_NODE_CONNECTION_DRIVERKEY_NAME,
                                    key_name.encode(),
                                    10,
                                    None)
    except pywintypes.error as e:
        # print(e.strerror, index)
        # sys.exit(1)
        return ""
    _, act_len, _ = struct.unpack('LLH', buf)
    buf = win32file.DeviceIoControl(handle,
                                IOCTL_USB_GET_NODE_CONNECTION_DRIVERKEY_NAME,
                                key_name.encode(),
                                act_len,
                                None)
    return buf[8:].decode('utf-16le', "backslashreplace")


def get_ext_hub_name(handle, index):
    hub_name = chr(index) + '\0'*9
    buf = win32file.DeviceIoControl(handle,
                                IOCTL_USB_GET_NODE_CONNECTION_NAME,
                                hub_name.encode(),
                                10,
                                None)
    _, act_len, _ = struct.unpack('LLH', buf)
    buf = win32file.DeviceIoControl(handle,
                                IOCTL_USB_GET_NODE_CONNECTION_NAME,
                                hub_name.encode(),
                                act_len,
                                None)
    return buf[8:].decode('utf-16le', "backslashreplace")


def get_str_desc(handle, conn_idx, str_idx):
    req = struct.pack('LBBHHH',
                  conn_idx,
                  0,
                  0,
                  (USB_STRING_DESCRIPTOR_TYPE<<8) | str_idx,
                  win32api.GetSystemDefaultLangID(),
                  MAXIMUM_USB_STRING_LENGTH)
    try:
        buf = win32file.DeviceIoControl(handle,
                                    IOCTL_USB_GET_DESCRIPTOR_FROM_NODE_CONNECTION,
                                    req,
                                    12+MAXIMUM_USB_STRING_LENGTH,
                                    None)
    except pywintypes.error as e:
         return '' # 'ERROR: no String Descriptor for index {}'.format(str_idx)
    if len(buf) > 16:
        return buf[14:].decode('utf-16le', "backslashreplace")
    return ''


def exam_hub(name, level, location):
    handle = open_dev(r'\\.\{}'.format(name))
    if not handle:
        return []
    buf = win32file.DeviceIoControl(handle,
                                IOCTL_USB_GET_NODE_INFORMATION,
                                None,
                                76,
                                None)
    devices = get_hub_ports(handle, buf[6], level, location)
    handle.close()
    return devices

def get_hub_ports(handle, num_ports, level, location):
    devices = []
    for idx in range(1, num_ports+1):
        info = chr(idx) + '\0'*34
        try:
            buf = win32file.DeviceIoControl(handle,
                                        IOCTL_USB_GET_NODE_CONNECTION_INFORMATION,
                                        info.encode(),
                                        34 + 11*30,
                                        None)
        except pywintypes.error as e:
            # print(e.winerror, e.funcname, e.strerror)
            pass

        _, vid, pid, vers, manu, prod, seri, _, ishub, _, stat = struct.unpack('=12sHHHBBB3s?6sL', buf[:35])

        if ishub:
            try:
                examed = exam_hub(get_ext_hub_name(handle, idx), level + 1, location + (idx,))
                if examed:
                    devices += examed
            except TypeError as ex:
                pass
        elif stat == 1:
            if (manu != 0 or prod != 0 or seri != 0):
                # print('{}  [Port{}] {}'.format('  '*level, idx, get_driverkey_name(handle, idx)))
                if manu != 0:
                    manu = get_str_desc(handle, idx, manu)
                if prod != 0:
                    prod = get_str_desc(handle, idx, prod)
                if seri != 0:
                    seri = get_str_desc(handle, idx, seri)
                devices.append(DeviceInfo(vid, pid, manu, prod, seri, location + (idx,)))
    return devices


def get_all_devices():
    devices = []

    for i in range(32):
        name = r"\\.\HCD{}".format(i)
        handle = open_dev(name)
        if not handle:
            continue

        root = get_root_hub_name(handle)
        # print('{}RootHub: {}'.format('\n' if i != 0 else '', root))

        dev_name = r'\\.\{}'.format(root)
        dev_handle = open_dev(dev_name)
        if not dev_handle:
            continue

        buf = win32file.DeviceIoControl(dev_handle,
                                    IOCTL_USB_GET_NODE_INFORMATION,
                                    None,
                                    76,
                                    None)
        devices += get_hub_ports(dev_handle, buf[6], 0, (i,))
        dev_handle.close()
        handle.close()

    return [dev for dev in devices if dev.serial_number not in ("","0","''")]

def main():
    devices = get_all_devices()
    print(devices)

if __name__ == '__main__':
    main()
