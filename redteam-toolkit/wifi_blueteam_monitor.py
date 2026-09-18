#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path

from common.pineapple_client import PineappleClient
from common.notify import notify_all

BASELINE_FILE = Path.home() / ".wifi_blueteam_baseline.json"
WATCHED_SSID = os.environ.get("WATCHED_SSID", "MyHomeNetwork")
NTFY_TOPIC = "homelab-wifi-ids"
SCAN_TIME_S = 20


def load_baseline():
    if BASELINE_FILE.exists():
        return json.loads(BASELINE_FILE.read_text())
    return {"bssids": []}


def save_baseline(baseline):
    BASELINE_FILE.write_text(json.dumps(baseline, indent=2))


def run_scan(client):
    status = client.recon_status()
    if status.get("captureRunning"):
        return []  # handshake capture owns the radio right now — skip this cycle
    client.recon_start(scan_time=SCAN_TIME_S)
    time.sleep(SCAN_TIME_S + 5)
    scans = client.recon_scans()
    if not scans:
        return []
    latest_id = scans[-1]["scan_id"]
    return client.recon_scan_results(latest_id)


def watched_aps(aps):
    return [ap for ap in aps if ap.get("ssid") == WATCHED_SSID and ap.get("bssid")]


def check_for_clones(aps, baseline):
    known = set(baseline["bssids"])
    seen = {ap["bssid"] for ap in aps}
    new = seen - known
    if known and new:
        return (f"New BSSID(s) broadcasting '{WATCHED_SSID}': {', '.join(sorted(new))} "
                f"— possible evil-twin/rogue AP. Known-good: {', '.join(sorted(known)) or 'none'}")
    return None


def main():
    client = PineappleClient()
    aps = watched_aps(run_scan(client))
    baseline = load_baseline()

    if not aps:
        return  # SSID not seen in this scan window — not itself an alert

    alert = check_for_clones(aps, baseline)
    if alert:
        notify_all(alert, "WiFi blue-team alert", NTFY_TOPIC)
        print(alert)

    baseline["bssids"] = sorted({ap["bssid"] for ap in aps} | set(baseline["bssids"]))
    save_baseline(baseline)


if __name__ == "__main__":
    main()
