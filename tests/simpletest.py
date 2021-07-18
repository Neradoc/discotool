import discotool

def display(texte):
	print(("-" * 70) + "\n-", texte + (" " * 20) + "-\n" + ("-" * 70))

display('get_devices_list()                             ')
deviceList,remainingPorts = discotool.get_devices_list()
print(deviceList)
print(remainingPorts)

display('devices_by_name("QT")                          ')
print(discotool.devices_by_name("QT"))

display('devices_by_drive("QTPY2040")                   ')
print(discotool.devices_by_drive("QTPY2040"))

display('devices_by_serial("DF609072DB8A2129")          ')
print(discotool.devices_by_serial("DF609072DB8A2129"))

display('devices_by_serial("123456789")                 ')
print(discotool.devices_by_serial("123456789"))

display('Device class/dictionnary                       ')
device = discotool.get_identified_devices()[0]
print(type(device))
print("Attributes:")
print(sorted([
	attr for
	attr in set(dir(device)) - set(dir({"un":1}))
	if attr[0:2] != "__"
]))
print("Dict indexes:")
print(tuple(x for x in device))
