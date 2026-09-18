# redteam-toolkit

Orchestration scripts tying the Pineapple (RF/radio layer) and the Pi (compute layer) together.
See `docs/security-toolkit.md` for the full architecture and `docs/pineapple-reference.md` for
the Pineapple API. **Everything here is for the user's own network only** — see the
authorization boundary in this README.

## Setup

On the Pi:
```
cp .env.example .env
# fill in PINEAPPLE_ROOT_PASS (from Vaultwarden), leave the rest at defaults unless changed
```
`.env` is never committed — only `.env.example` (empty template) lives in this repo.

### Discord notifications

Every notify call posts straight to a Discord webhook (`DISCORD_WEBHOOK_URL` in `.env`) — no ntfy
involved, the user doesn't use it. To (re)configure: in the target server, Server Settings →
Integrations → Webhooks → New Webhook → pick a channel → Copy Webhook URL, set
`DISCORD_WEBHOOK_URL=<that URL>` in `.env`, restart `security-hub.service`. If unset, notify_all()
silently no-ops rather than erroring.

## `handshake_capture.py` — capture + crack automation

Drives the full rogue-client PMKID capture pipeline: frees the shared
radio, runs `hcxdumptool` on the Pineapple against specific BSSIDs, pulls the pcapng, restarts
`pineapd`/`pineapple` (required afterward or the API state desyncs from the radio), converts with
`hcxpcapngtool`, and cracks with `hashcat -m 22000`. Reports + notifies to Discord.

```
source .env && export $(cut -d= -f1 .env)
python3 handshake_capture.py --bssid AA:BB:CC:DD:EE:FF --channel 6 \
  --duration 90 --crack-budget 600 --confirm-own-network
```

`--confirm-own-network` is mandatory — the script will not run without it.

Add `--deauth` (and optionally `--deauth-seconds 15`, the default) to force a reconnection via
`mdk4` partway through the capture window — needed if the router validates the MIC before replying
(confirmed 2026-07-08: passive capture alone got nothing against `MyHomeNetwork`, `--deauth` got
a real crackable handshake from an actual client). Only targets the first `--bssid`/`--channel`
pair. Requires `mdk4` on the Pineapple: `opkg install mdk4` over SSH (the Pineapple GUI infusion of
the same name only ships the UI, not the binary).

## `wifi_blueteam_monitor.py` — evil-twin / rogue-AP detector

Polls the Pineapple's recon scan results for the watched SSID (`WATCHED_SSID`, default
`MyHomeNetwork`), maintains a local baseline of known-good BSSIDs, and alerts to Discord the
moment a *new* BSSID starts broadcasting the same SSID — the signature of someone running an evil
twin against this network. Deploy via the included systemd timer
(`systemd/wifi-blueteam-monitor.{service,timer}`, paths already point at
`~/tools/redteam-toolkit` on the Pi) — copy both units to `/etc/systemd/system/`, then
`sudo systemctl enable --now wifi-blueteam-monitor.timer`.

## Status

Live-verified end to end 2026-07-08 against the real Pineapple and the user's own network,
including a full deauth-forced capture that yielded real crackable material. See
`docs/security-toolkit.md` for the `--backend-vector-width 1` hashcat fix (mode 22000 segfaults on
this Pi's CPU backend without it) and the deauth-vs-passive-PMKID finding.
