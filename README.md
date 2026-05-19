````
# Monitor Internet Uptime

A lightweight Windows system tray app that monitors your internet connection and notifies you when it drops or comes back.

## Features

- **Tray icon** — green when online, red when offline
- **Toast notifications** — native Windows alerts on status change
- **Logs window** — view all connection events via tray menu
- **False positive protection** — only triggers after consecutive failures

## Setup

```bash
pip install Pillow pystray
python monitornettray.pyw
```

Or just run `dist/monitornettray.exe` directly — no install needed.

## Configuration

Open `monitornettray.pyw` and edit these at the top:

| Variable | Default | Description |
|---|---|---|
| `TARGET_URL` | `https://www.google.com` | URL to ping |
| `CHECK_INTERVAL` | `5` | Seconds between checks |
| `CONSECUTIVE_THRESHOLD` | `2` | Failed checks before marking offline |

## Building the EXE

```bash
python -m PyInstaller --noconsole --onefile monitornettray.pyw
```

Output will be in `dist/monitornettray.exe`.

## Notes

- Logs are in-memory only — they reset when the app closes
- Notifications use PowerShell under the hood; works in both script and EXE
````