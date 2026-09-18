# security-hub

The "one shortcut" dashboard: a single page bringing every Pi + Pineapple security/CTF tool
together — live Pineapple status, the blue-team baseline, a self-service handshake-capture form,
recent capture reports, and an organized cheat sheet of every CLI tool and Pineapple infusion
(`tools.yaml` is the single source of truth — edit it, no HTML changes needed).

Flask + PyYAML, both apt-installed on the Pi (no venv needed — Debian 13 ships packaged
`python3-flask`/`python3-yaml`). Reuses `redteam-toolkit`'s `PineappleClient` and
`handshake_capture.run_capture` directly (`sys.path` includes `~/tools/redteam-toolkit`) so there
is exactly one implementation of the capture pipeline, not a duplicate.

## Deploy (already done on homelab, for reference/redeploys)

```
rsync -az --exclude='.env' security-hub/ homelab:~/tools/security-hub/
ssh homelab 'sudo cp ~/tools/security-hub/systemd/security-hub.service /etc/systemd/system/ && \
  sudo systemctl daemon-reload && sudo systemctl enable --now security-hub.service'
ssh homelab 'tailscale serve --bg --https=8454 http://127.0.0.1:8454'
```

Loopback-bound (`127.0.0.1:8454`) like every other backend on this box, exposed tailnet-only via
`tailscale serve`. URL: `https://homelab.tailnet.ts.net:8454`.

## Security note on the capture form

BSSID/channel input from the form is validated against a strict allowlist regex
(`handshake_capture.validate_bssids`/`validate_channels`) *before* anything is interpolated into
the SSH command sent to the Pineapple — the same validation the CLI path uses. This is the
injection boundary; do not bypass it when editing `app.py`.
