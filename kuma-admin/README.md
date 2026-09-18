# kuma-admin

Kuma has no REST API for mutations — everything (add/edit monitors, read notifications) goes
through Socket.IO events. `kuma_client.py` wraps the handful this project needs.

## Setup (already done on the Pi)

```
python3 -m venv ~/tools/.kuma-venv
~/tools/.kuma-venv/bin/pip install python-socketio[client] websocket-client requests
```

Credentials come from `~/.homelab-creds.env` on the Pi (`KUMA_URL`, `KUMA_USER`, `KUMA_PASS`) —
never in this repo. See that file for the broader "don't ask for homelab credentials" policy.

## Usage

```
set -a && source ~/.homelab-creds.env && set +a
~/tools/.kuma-venv/bin/python3 kuma_client.py   # prints current monitors + notifications
```

`KumaClient.add_monitor(name, url, notification_ids={"1": True, "2": True})` is idempotent — it
skips silently if a monitor with that name already exists, so it's safe to re-run.

## Status

Live-verified 2026-07-09: confirmed the Discord notification (`isDefault`+`applyExisting`) had
correctly reached all 18 pre-existing monitors (checked each monitor's real
`notificationIDList`, not just the notification's own config flags), then added the WiFi
Pineapple (`http://192.168.1.50:1471`) as monitor #19 with both notifications attached.
