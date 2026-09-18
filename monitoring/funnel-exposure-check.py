#!/usr/bin/env python3
# Detects drift in Tailscale Funnel (public exposure) config: new ports made
# public, or new paths appearing under an already-public port (e.g. Ente's
# storage-replication paths leaking which backends are configured). Config
# only changes via manual `tailscale funnel` edits, so this is a state-drift
# check, not a liveness check — silent unless the exposed surface changed.
import difflib
import json
import subprocess
import urllib.request
from pathlib import Path

STATE_FILE = Path("/etc/homelab-funnel-baseline.txt")
ENV_FILE = Path("/home/homelab/tools/redteam-toolkit/wifi-blueteam-monitor-discord.env")


def load_webhook():
    if not ENV_FILE.exists():
        return None
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith("DISCORD_WEBHOOK_URL="):
            return line.split("=", 1)[1].strip()
    return None


def current_funnel_state():
    # `tailscale funnel status` iterates a Go map internally, so entries come
    # back in a different order on every single invocation even when nothing
    # about the exposed surface changed. Sorting blocks by their URL before
    # comparing is what makes this a real drift check instead of a random
    # 6-hourly false alarm.
    out = subprocess.run(
        ["tailscale", "funnel", "status"],
        capture_output=True, text=True, check=True,
    ).stdout
    blocks = []
    current_block = None
    for line in out.splitlines():
        if line.startswith("https://"):
            current_block = [line.strip()] if "(Funnel on)" in line else None
            if current_block is not None:
                blocks.append(current_block)
        elif current_block is not None and line.strip().startswith("|--"):
            current_block.append(line.strip())
    blocks.sort(key=lambda block: block[0])
    return "\n".join(line for block in blocks for line in block)


def send_alert(diff_text, webhook):
    payload = {
        "content": "@everyone",
        "embeds": [{
            "title": "Tailscale Funnel exposure changed",
            "description": f"Public-facing config drifted from baseline:\n```\n{diff_text[:1500]}\n```",
            "color": 15158332,
        }]
    }
    req = urllib.request.Request(
        webhook,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "curl/8.5.0",
        },
    )
    urllib.request.urlopen(req, timeout=10)


def main():
    current = current_funnel_state()
    if not STATE_FILE.exists():
        STATE_FILE.write_text(current)
        return

    baseline = STATE_FILE.read_text()
    if current.strip() == baseline.strip():
        return

    webhook = load_webhook()
    if webhook:
        diff = "\n".join(difflib.unified_diff(
            baseline.splitlines(), current.splitlines(),
            fromfile="baseline", tofile="current", lineterm="",
        ))
        send_alert(diff, webhook)
    STATE_FILE.write_text(current)


if __name__ == "__main__":
    main()
