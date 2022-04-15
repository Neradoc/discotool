import discotool

def display(texte):
	print(("-" * 70) + "\n-", texte.ljust(70-3) + "-\n" + ("-" * 70))

# display('get_devices_list()                             ')
# deviceList,remainingPorts = discotool.get_devices_list()
# print(deviceList)
# print(remainingPorts)

# display('Device class/dictionnary                       ')
for device in discotool.get_identified_devices():
	display(device.name)
	# print(type(device))
# 	print("Attributes:")
# 	print(sorted([
# 		attr for
# 		attr in set(dir(device)) - set(dir({"un":1}))
# 		if attr[0:2] != "__"
# 	]))
	print("Dict indexes:")
# 	for x in device:
# 		print(f"{x:12s} : {device[x]}")
	print("location :", device["usb_location"])

display("")
