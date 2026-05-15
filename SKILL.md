---
name: coder-buddy-esp32
description: Call the local Coder Buddy REST API from assistant hooks when approval or attention events happen.
---

# Coder Buddy API

Use this exact base URL:

```text
http://192.168.31.219
```

Do not guess or rediscover the IP unless the user explicitly says the device has been redeployed or the IP changed.

## Hook Calls

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
