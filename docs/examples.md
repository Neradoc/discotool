#### A few boards running whatever (on macOS).
(I almost always rename my CIRCUITPY drive)
```
- Feather STM32F405 Express ---------------------------------------------
	Adafruit Industries LLC [SN:C100730090052524E4039302]
	/dev/cu.usbmodem144443201
	/Volumes/STM32F4 (code.py) v6.0.1
- Circuit Playground Bluefruit ------------------------------------------
	Adafruit Industries LLC [SN:AB7F0B6289E27E25]
	/dev/cu.usbmodem144443131
	/Volumes/CIRCUITBLUE (code.py) v6.0.0
- CLUE nRF52840 Express -------------------------------------------------
	Adafruit Industries LLC [SN:F88EE0399C0E1FC6]
	/dev/cu.usbmodem144443111
	/Volumes/CPCLUE (code.py) v6.0.1
- QT Py M0 Haxpress -----------------------------------------------------
	Adafruit Industries LLC [SN:E60C9708935345050213E223E102F0FF]
	/dev/cu.usbmodem144443301
	/Volumes/QTPYHX (code.py) v6.1.0-rc.0
```
##### Some CIRCUITPY goodness (all 3 connected at the same time)
```
- Feather M0 Adalogger --------------------------------------------------
	Adafruit Industries LLC [SN:6EEC20D45305D41502020253B09111FF]
	/dev/cu.usbmodem144443141
	/Volumes/CIRCUITPY 2 (code.py) v5.3.1
- Trinket M0 ------------------------------------------------------------
	Adafruit Industries LLC [SN:7EE04DF33323B4050213E283244181FF]
	/dev/cu.usbmodem144443131
	/Volumes/CIRCUITPY v6.0.1
- Feather M4 Express ----------------------------------------------------
	Adafruit Industries LLC [SN:7FEC7DFB359333350202026390E321FF]
	/dev/cu.usbmodem144443121
	/Volumes/CIRCUITPY 1 (code.py) v5.2.0
```
##### Not Circuitpython
```
- Arduino Micro ---------------------------------------------------------
	Arduino LLC
	/dev/cu.usbmodem144443121
```
##### Micro:Bit V2 has quotation marks in its USB description for some reason
```
- "BBC micro:bit CMSIS-DAP" ---------------------------------------------
	ARM [SN:9904360258994e45004b900e00000025000000009796990b]
	/dev/cu.usbmodem144443142
	/Volumes/MICROBIT
- BBC micro:bit CMSIS-DAP -----------------------------------------------
	ARM [SN:9901000052964e4500290010000000100000000097969901]
	/dev/cu.usbmodem144443122
	/Volumes/MICROBIT 1
```
##### Huzzah ESP8266
```
- CP2104 USB to UART Bridge Controller ----------------------------------
	Silicon Labs [SN:010DAFCB]
	/dev/cu.usbserial-010DAFCB
Huzzah 32
- CP2104 USB to UART Bridge Controller ----------------------------------
	Silicon Labs [SN:01426E16]
	/dev/cu.usbserial-01426E16
```
##### Adafruit's Serial CP2104 Friend
```
- CP2104 USB to UART Bridge Controller ----------------------------------
	Silicon Labs [SN:01C78962]
	/dev/cu.usbserial-01C78962
```
##### WICED Feather has two serial ports
```
- WICED Feather Board ---------------------------------------------------
	Adafruit Industries [SN:00000000001B]
	/dev/cu.usbmodem00000000001B1
	/dev/cu.usbmodem00000000001B3
```
##### A radio feather running arduino
```
- Feather M0 ------------------------------------------------------------
	Adafruit [SN:2BFDC4A7514D503259202020FF10102F]
	/dev/cu.usbmodem144443141
```
##### The same in bootloader (double click)
```
- comm_device -----------------------------------------------------------
	[SN:]
	/dev/cu.usbmodem144443141
```
##### Some of the boards in bootloader mode
```
- QT Py M0 --------------------------------------------------------------
	Adafruit Industries [SN:8079C06E50543539322E3120FF0F201E]
	/dev/cu.usbmodem144443301
	/Volumes/QTPY_BOOT
- Bluefruit nRF52840 DFU ------------------------------------------------
	Adafruit Industries [SN:52E72E9826B0F7BA]
	/dev/cu.usbmodem144443141
	/Volumes/CPLAYBTBOOT
- Trinket M0 ------------------------------------------------------------
	Adafruit Industries [SN:3FD40EE7504B3233382E3120FF181442]
	/dev/cu.usbmodem144443131
	/Volumes/TRINKETBOOT 1
- Feather M4 Express ----------------------------------------------------
	Adafruit Industries [SN:BFD7CEF75333395336202020FF123E09]
	/dev/cu.usbmodem144443121
	/Volumes/FEATHERBOOT
- Trinket M0 ------------------------------------------------------------
	Adafruit Industries
	/dev/cu.usbmodem144443111
	/Volumes/TRINKETBOOT
```
##### This DFU does not use a serial port I guess ?
```
- WICED Feather DFU -----------------------------------------------------
	Adafruit Industries [SN:00000000001C]
```
##### FeatherS2
- **ROM bootloader**  
```
- ESP32-S2 --------------------------------------------------------------
	Espressif [SN:0]
	/dev/cu.usbmodem01
```
- **UF2 bootloader (no serial)**  
```
- FeatherS2 -------------------------------------------------------------
	Unexpected Maker [SN:7CDFA103B7B4]
	/Volumes/UFTHRS2BOOT
```  
- **Circuitpython running (drive renamed)**  
```
- FeatherS2 -------------------------------------------------------------
	UnexpectedMaker [SN:7CDFA103B674]
	/dev/cu.usbmodem7CDFA103B6741
	/Volumes/FEATHERS2 v6.1.0-rc.0
```
##### Unmounting with `discotool eject` (Mac only for now)
```
- EJECTING DRIVES -------------------------------------------------------
Ejecting: FEATHERS2
Ejecting: STM32F4
Ejecting: MICROBIT
Ejecting: CIRCUITBLUE
Ejecting: CPCLUE
```
