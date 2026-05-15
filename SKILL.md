---
name: coder-buddy-esp32
description: Control the local Coder Buddy ESP32 attention device from assistant hooks or agent workflows. Use when approval, permission, review, waiting-for-user, or attention events should trigger, stop, reset, diagnose, or configure the physical device via MCP tools first and HTTP fallback second.
---

# Coder Buddy API

Prefer MCP tools. Use HTTP only when MCP tooling is unavailable.

Use this exact base URL:

```text
http://192.168.31.219
```

Do not guess or rediscover the IP unless the user explicitly says the device has been redeployed or the IP changed.

## MCP Server

Start the bundled stdio MCP server from this skill folder:

```bash
BUDDY_IP=192.168.31.219 node coder_buddy_mcp.mjs
```

`coder_buddy_mcp.mjs` is stored next to this `SKILL.md` file and has no npm package dependencies. A runtime with only this skill folder can start it directly.

## MCP Tools

Use these tools before shell/curl commands:

- `coder_buddy_trigger`
  - Use when an approval or attention event starts.
  - Input: `{}`
  - Expected result shape: the same status payload as `GET /status`.
- `coder_buddy_stop`
  - Use when the approval is handled, rejected, cancelled, or no longer needs attention.
  - Input: `{}`
  - Expected result shape: the same status payload as `GET /status`.
- `coder_buddy_reset`
  - Use for diagnostics, cleanup, or explicitly clearing the device state.
  - Input: `{}`
  - Expected result shape: the same status payload as `GET /status`.
- `coder_buddy_status`
  - Use for diagnostics before or after an alert event.
  - Input: `{}`
  - Expected result shape: status fields include `ip`, `level`, `running`, `track`, `tracks`, `device`, and `max_level`.
- `coder_buddy_set_track`
  - Use only when the user explicitly asks to change the WAV track.
  - Input: `{ "track": "approve_soft.wav" }`
  - Expected result shape: the same status payload as `GET /status`.

Tool behavior mirrors the REST API:

- `coder_buddy_trigger` maps to `POST /trigger` and increments level by 1, up to 10.
- `coder_buddy_stop` maps to `POST /stop` and decrements level by 1. When the level reaches 0, the device stops its current alert state.
- `coder_buddy_reset` maps to `POST /reset` and clears level to 0.
- `coder_buddy_status` maps to `GET /status`.
- `coder_buddy_set_track` maps to `POST /config/track`.

If an MCP call fails because the MCP server is unavailable, use the HTTP fallback commands below.

## HTTP Fallback Calls

Call this when an approval or attention event starts:

```bash
curl -s -X POST http://192.168.31.219/trigger
```

`/trigger` increments the active level by 1, up to 10.

Call this when the approval is handled, rejected, cancelled, or no longer needs attention:

```bash
curl -s -X POST http://192.168.31.219/stop
```

`/stop` decrements the active level by 1. When the level reaches 0, the device stops its current alert state.

Use this for diagnostics:

```bash
curl -s http://192.168.31.219/status
```

Expected status fields include `ip`, `level`, `running`, `track`, `tracks`, `device`, and `max_level`.

## Web UI

Open this URL on the LAN to select the WAV track used by `/trigger`:

```text
http://192.168.31.219/
```
