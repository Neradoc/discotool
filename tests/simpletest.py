import discotool

deviceList,remainingPorts = discotool.list_devices()
print(deviceList)

discotool.addCircuitpythonInfo(deviceList)
print(deviceList)
