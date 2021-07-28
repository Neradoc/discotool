from .usbinfos import (
	get_devices_list,
	get_identified_devices,
	get_unidentified_ports,
	devices_by_name,
	devices_by_drive,
	devices_by_serial,
)

try:
	from ._version import version as __version__
except:
	__version__ = "0.0.0-auto.0"
