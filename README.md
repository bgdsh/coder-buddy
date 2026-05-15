# Coder Buddy

Coder Buddy is an ESP32-S3 attention device for AI-assisted coding workflows. It gives an agent a tiny physical presence: when an approval, permission prompt, review, or waiting-for-user moment needs attention, the device can light up, move a servo, and play a WAV alert.

The project includes:

- MicroPython firmware for an ESP32-S3 board
- A self-contained Web UI served directly by the device
- WAV alert generation and upload tooling
- A dependency-free stdio MCP server for AI agents
- A self-contained skill entry point for agent runtimes
- Playwright and MCP smoke tests

## Features

- REST API for triggering, stopping, resetting, and inspecting alerts
- Chinese Web UI at `/` and `/index.html`
- Selectable WAV alert track from the browser
- Servo, RGB LED, button, and I2S amplifier support
- Emergency physical button to clear the alert state
- MCP tools for agent integrations:
  - `coder_buddy_trigger`
  - `coder_buddy_stop`
  - `coder_buddy_reset`
  - `coder_buddy_status`
  - `coder_buddy_set_track`

## Hardware

The current firmware targets an ESP32-S3 board running MicroPython.

### Bill of Materials

| Item | Quantity | Notes |
| --- | ---: | --- |
| ESP32-S3 development board | 1 | Board with USB serial support. The current device was verified on an ESP32-S3 with 16MB Flash and 8MB PSRAM. |
| Continuous-rotation servo | 1 | Controlled by PWM on GPIO 14. A positional servo can also work after tuning the angle constants. |
| Common-cathode RGB LED | 1 | Uses separate PWM pins for red, green, and blue. Add current-limiting resistors as needed. |
| Momentary push button | 1 | Emergency clear button, wired active-low to GPIO 7. |
| I2S amplifier module | 1 | For WAV alert playback. Example modules include MAX98357A-style I2S amps. |
| Speaker | 1 | Match the speaker impedance and power rating to the amplifier module. |
| External 5V power supply | 1 | Recommended for the servo and amplifier. Share ground with the ESP32-S3. |
| Breadboard or perfboard | 1 | For prototyping or permanent assembly. |
| Jumper wires | As needed | Keep servo power wiring tidy to reduce noise. |
| Resistors for RGB LED | 3 | Typical values depend on the LED and supply voltage. |

Default GPIO mapping:

| Function | GPIO |
| --- | --- |
| Servo PWM | 14 |
| RGB LED red | 4 |
| RGB LED green | 5 |
| RGB LED blue | 6 |
| Emergency button | 7 |
| I2S DIN | 16 |
| I2S BCLK | 17 |
| I2S LRC | 18 |
| Amplifier enable / SD | 15 |

See [docs/wiring.md](docs/wiring.md) for the wiring diagram, GPIO table, and power notes.

## Repository Layout

```text
.
├── AGENTS.md                 # Maintenance notes for coding agents
├── SKILL.md                  # Agent-facing skill instructions
├── coder_buddy_mcp.mjs       # Dependency-free stdio MCP server
├── src/
│   ├── config.py             # Hardware pins and firmware settings
│   ├── main.py               # MicroPython firmware
│   ├── index.html            # Device-hosted Web UI
│   └── secrets.example.py    # Wi-Fi credentials template
├── audio/                    # Generated WAV alert tracks
├── scripts/                  # Upload, WAV generation, and smoke-test helpers
└── docs/                     # Hardware docs
```

## Requirements

For firmware deployment:

- Python 3
- `pyserial`
- `esptool`
- ESP32-S3 MicroPython firmware image
- A local `src/secrets.py` copied from `src/secrets.example.py`

For UI and MCP tests:

- Node.js 18+ recommended
- npm
- Playwright Chromium installed by `make check-ui-setup`

## Configure Wi-Fi

Create local Wi-Fi credentials before uploading firmware code:

```bash
cp src/secrets.example.py src/secrets.py
```

Edit `src/secrets.py` with your network SSID and password. This file is ignored by git and should not be committed.

## Common Commands

List serial ports:

```bash
make list-ports
```

Identify the connected ESP32:

```bash
make identify PORT=/dev/cu.usbmodem101
```

Flash MicroPython:

```bash
make flash PORT=/dev/cu.usbmodem101
```

Upload firmware code, Web UI, and WAV assets:

```bash
make upload PORT=/dev/cu.usbmodem101
```

Check the deployed device status:

```bash
make status
```

Use a custom device IP:

```bash
make status BUDDY_IP=192.168.31.219
```

## REST API

Default base URL:

```text
http://192.168.31.219
```

Endpoints:

| Method | Path | Behavior |
| --- | --- | --- |
| `POST` | `/trigger` | Increment alert level by 1, up to 10. |
| `POST` | `/stop` | Decrement alert level by 1. At 0, stop the alert. |
| `POST` | `/reset` | Clear alert level to 0. |
| `GET` | `/status` | Return current status JSON. |
| `GET` | `/tracks` | List available WAV tracks. |
| `POST` | `/config/track` | Save the selected WAV track. |

Example:

```bash
curl -s -X POST http://192.168.31.219/trigger
curl -s http://192.168.31.219/status
curl -s -X POST http://192.168.31.219/reset
```

## Web UI

After uploading, open the device in a browser:

```text
http://192.168.31.219/
```

The ESP32 serves `src/index.html` from `/index.html`. The page is standalone HTML/CSS/JavaScript and talks to the firmware API with AJAX.

## MCP Server

The repository includes a dependency-free stdio MCP server next to `SKILL.md`:

```bash
BUDDY_IP=192.168.31.219 node coder_buddy_mcp.mjs
```

For repository usage:

```bash
make mcp
make check-mcp
```

`make check-mcp` starts the MCP server over stdio, verifies the tool list, and calls `coder_buddy_status` against the configured device.

## Agent Skill

`SKILL.md` and `coder_buddy_mcp.mjs` are the source of truth for the Coder Buddy skill. Sync them into local agent skill directories with:

```bash
make sync-skill
make check-skill-sync
```

This installs matching copies to:

```text
~/.agents/skills/coder-buddy-esp32/
~/.claude/skills/coder-buddy-esp32/
```

The installed skill folder is self-contained: it only needs `SKILL.md`, `coder_buddy_mcp.mjs`, and Node.js.

## Testing

Install UI test dependencies and Chromium once:

```bash
make check-ui-setup
```

Run Web UI smoke tests:

```bash
make check-ui
```

Run MCP smoke tests:

```bash
make check-mcp
```

Run both after changing UI or agent integration code.

## Development Notes

- Keep firmware behavior in `src/main.py` and hardware mapping in `src/config.py`.
- Keep the Web UI self-contained in `src/index.html`; do not rely on CDNs or build output on the device.
- Keep `SKILL.md` concise and agent-facing.
- Keep `coder_buddy_mcp.mjs` dependency-free so a copied skill folder can run without the full repository.
- Use [AGENTS.md](AGENTS.md) for deployment details, hardware maintenance notes, and local troubleshooting.

## License

No license has been declared yet. Add a license before accepting external contributions or publishing release artifacts.
