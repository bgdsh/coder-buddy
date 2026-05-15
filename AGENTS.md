# Coder Buddy ESP32 Maintenance Notes

This repository contains the ESP32-S3 MicroPython firmware and deployment assets for the Coder Buddy device.

## Deployed Device

- API base URL: `http://192.168.31.219`
- Device name: `coder-buddy`
- Serial port used during deployment: `/dev/cu.usbmodem101`
- Board verified during deployment: ESP32-S3, 16MB Flash, 8MB Embedded PSRAM
- MicroPython firmware: `v1.28.0`, build `ESP32_GENERIC_S3-SPIRAM_OCT`
- Firmware file: `firmware/ESP32_GENERIC_S3-SPIRAM_OCT-20260406-v1.28.0.bin`

## Repository Commands

```bash
make list-ports
make identify PORT=/dev/cu.usbmodem101
make flash PORT=/dev/cu.usbmodem101
make verify PORT=/dev/cu.usbmodem101
make upload PORT=/dev/cu.usbmodem101
make status
```

Notes:
- `make flash` erases the board and flashes MicroPython.
- `make upload` uploads `src/*.py` and generated WAV files.
- `make status` calls the deployed API at `BUDDY_IP`, defaulting to `192.168.31.219`.
- `make verify` enters raw REPL and can interrupt the running app. Run `make reset PORT=/dev/cu.usbmodem101` afterward before testing the HTTP API.
- Serial upload uses `scripts/mpy_tool.py` because `mpremote fs cp` was unreliable when launched through `make` in this environment.

## Configuration

Wi-Fi credentials are in local-only `src/secrets.py` so they can be changed before upload. Do not commit real credentials. Use `src/secrets.example.py` as the tracked template.

Hardware mapping is in `src/config.py`:
- Servo PWM: GPIO 14
- Servo neutral: 90 degrees. This is intentional for a continuous-rotation servo; at level 0 and on boot, the servo should receive the neutral signal instead of `SERVO_MIN_ANGLE`.
- RGB LED: R GPIO 4, G GPIO 5, B GPIO 6
- RGB LED mode: common cathode by default
- Button OUT: GPIO 7, active-low with pull-up by default
- I2S amp DIN: GPIO 16
- I2S amp BCLK: GPIO 17
- I2S amp LRC: GPIO 18
- Amp enable / SD: GPIO 15, active-high by default
- Servo angle range: 80 to 100 degrees

Servo behavior:
- On boot and at API level 0, the firmware writes `SERVO_NEUTRAL_ANGLE` so the servo should stop.
- While active, the servo alternates between `SERVO_MIN_ANGLE` and `SERVO_MAX_ANGLE`.
- For a positional servo, tune the three servo angle values in `src/config.py`.
- For a continuous-rotation servo, tune `SERVO_NEUTRAL_ANGLE` first. If it creeps at 90, adjust it by 1-2 degrees until it stops.

Audio assets are uploaded from `audio/*.wav` to `/audio` on the device. Generated test tracks:
- `approve_soft.wav`
- `approve_ping.wav`
- `approve_alert.wav`

## API Behavior

- `POST /trigger`: increments level by 1, max 10.
- `POST /stop`: decrements level by 1; at 0, alert state stops.
- `POST /reset`: clears level to 0.
- `GET /status`: returns device status JSON.
- `GET /tracks`: returns available WAV tracks.
- `POST /config/track`: saves selected WAV track from the Web UI.

The physical button is the emergency clear action. It resets level to 0 and stops servo movement, LED blinking, and audio playback.

## Project Notes

- Keep `SKILL.md` focused on the assistant-facing API URL and hook usage only. Do not put board model, serial port, flashing instructions, or firmware details there.
- Put maintenance, deployment, hardware, and troubleshooting notes in this `AGENTS.md`.
- `src/secrets.py` contains local Wi-Fi credentials for deployment and is ignored by git. Keep `src/secrets.example.py` as the committed template.
- The firmware binary is intentionally ignored by git via `.gitignore`; download or regenerate it when needed.
- Generated `__pycache__` directories are ignored and should not be committed.
