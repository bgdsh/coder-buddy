PORT ?= /dev/cu.usbmodem101
MPREMOTE ?= mpremote
MPREMOTE_RETRY ?= ./scripts/mpremote_retry.sh
MPY_TOOL ?= python3 scripts/mpy_tool.py
ESPTOOL ?= python3 -m esptool
FIRMWARE ?= firmware/ESP32_GENERIC_S3-SPIRAM_OCT-20260406-v1.28.0.bin
BUDDY_IP ?= 192.168.31.219

.PHONY: list-ports identify erase flash verify wavs upload upload-code upload-audio mkdirs reset status skill

list-ports:
	python3 -m serial.tools.list_ports -v

identify:
	$(ESPTOOL) --port $(PORT) flash-id

erase:
	$(ESPTOOL) --port $(PORT) erase-flash

flash: erase
	$(ESPTOOL) --port $(PORT) --baud 460800 write-flash -z --flash-mode dout 0 $(FIRMWARE)

verify:
	$(MPY_TOOL) --port $(PORT) exec "import sys,os,gc; print(sys.implementation); print(os.uname()); print('mem_free', gc.mem_free())"

wavs:
	python3 scripts/make_wavs.py

mkdirs:
	$(MPY_TOOL) --port $(PORT) exec "import os\ntry:\n    os.mkdir('audio')\nexcept OSError:\n    pass\n"

upload-code:
	$(MPY_TOOL) --port $(PORT) upload src/config.py:config.py src/secrets.py:secrets.py src/main.py:main.py

upload-audio: wavs
	$(MPY_TOOL) --port $(PORT) upload audio/approve_soft.wav:audio/approve_soft.wav audio/approve_ping.wav:audio/approve_ping.wav audio/approve_alert.wav:audio/approve_alert.wav

upload: upload-code upload-audio reset

reset:
	$(MPY_TOOL) --port $(PORT) reset

status:
	@for n in 1 2 3 4 5; do curl -s --max-time 2 http://$(BUDDY_IP)/status && exit 0; sleep 1; done; exit 1

skill:
	$(MPY_TOOL) --port $(PORT) exec "import network; print(network.WLAN(network.STA_IF).ifconfig()[0])"
