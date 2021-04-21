import discotool

deviceList,remainingPorts = discotool.get_devices_list()
print(deviceList)

discotool.addCircuitpythonInfo(deviceList)
print(deviceList)
