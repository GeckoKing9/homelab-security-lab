#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import yaml
from flask import Flask, abort, jsonify, redirect, render_template, request, send_file

REPO_ROOT = Path(__file__).resolve().parent
TOOLKIT_ROOT = Path.home() / "tools" / "redteam-toolkit"
CAPTURES_DIR = Path.home() / "captures"
BASELINE_FILE = Path.home() / ".wifi_blueteam_baseline.json"

sys.path.insert(0, str(TOOLKIT_ROOT))
from common.pineapple_client import PineappleClient  # noqa: E402
from handshake_capture import (  # noqa: E402
    ValidationError, run_capture, stop_capture_and_restart_daemons,
    validate_bssids, validate_channels,
)

app = Flask(__name__)

QUICK_LINKS = [
    {"name": "Pineapple web UI", "url": "http://192.168.1.50:1471"},
    {"name": "Homepage", "url": "https://homelab.tailnet.ts.net:8446"},
    {"name": "Uptime Kuma", "url": "https://homelab.tailnet.ts.net:8447"},
    {"name": "Dockge", "url": "https://homelab.tailnet.ts.net:8451"},
    {"name": "Vaultwarden", "url": "https://homelab.tailnet.ts.net:8444"},
    {"name": "NetAlertX (needs SSH -L 20211:127.0.0.1:20211 homelab)", "url": "http://localhost:20211"},
]


def load_tools():
    return yaml.safe_load((REPO_ROOT / "tools.yaml").read_text())


def load_baseline():
    if BASELINE_FILE.exists():
        return json.loads(BASELINE_FILE.read_text())
    return {"bssids": []}


def phase_seconds_remaining(phase, meta):
    """Each phase has its own clock — lumping duration+crack_budget into one countdown
    made the number wrong (it kept counting down the crack budget even while still
    capturing). Only "capturing" and "cracking" have a real budget to count against;
    the pull/convert steps are normally a few seconds and don't get a fake ETA."""
    now = time.time()
    if phase == "capturing" and meta.get("started_at"):
        return max(0, round(meta["duration"] - (now - meta["started_at"])))
    if phase == "cracking" and meta.get("cracking_started_at"):
        return max(0, round(meta["crack_budget"] - (now - meta["cracking_started_at"])))
    return None


def recent_captures(limit=10):
    """Each run's meta.json (written live by run_capture) drives phase + countdown math —
    report.txt only appears once the whole pipeline is finished."""
    if not CAPTURES_DIR.exists():
        return []
    runs = sorted(CAPTURES_DIR.iterdir(), reverse=True)[:limit]
    out = []
    for run in runs:
        report = run / "report.txt"
        meta_file = run / "meta.json"
        meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
        phase = meta.get("phase", "unknown")
        hash_file = run / "hash.22000"
        entry = {
            "when": run.name,
            "phase": phase,
            "done": report.exists(),
            "result": report.read_text().strip() if report.exists() else None,
            # a non-empty hash.22000 is the crackable artifact to pull onto the GPU box
            "hash_available": hash_file.exists() and hash_file.stat().st_size > 0,
        }
        if not entry["done"]:
            remaining = phase_seconds_remaining(phase, meta)
            if remaining is not None:
                entry["seconds_remaining"] = remaining
        out.append(entry)
    return out


def pineapple_snapshot():
    try:
        client = PineappleClient()
        status = client.recon_status()
        settings = client.pineap_settings()["settings"]
        modules = [m["title"] for m in client.modules_installed()]
        return {
            "reachable": True,
            "recon_running": status.get("scanRunning"),
            "capture_running": status.get("captureRunning"),
            "karma_enabled": settings.get("karma"),
            "installed_modules": modules,
        }
    except Exception as e:
        return {"reachable": False, "error": str(e)}


def known_networks():
    """SSID -> BSSID/channel lookup from the most recent completed recon scan, strongest
    signal first (closest to 0 dBm = strongest). This is what the capture form's BSSID field
    actually wants: the MAC address of a specific access point, not a device MAC. Reading the
    last scan (up to 10 min stale, refreshed by the blue-team monitor timer) avoids blocking
    the page on a live 20s scan.
    """
    try:
        client = PineappleClient()
        scans = client.recon_scans()
        if not scans:
            return []
        aps = client.recon_scan_results(scans[-1]["scan_id"])
        seen = {}
        for ap in aps:
            ssid = ap.get("ssid")
            if not ssid:
                continue  # hidden/blank SSID — not useful for a name-based lookup
            seen[(ssid, ap["bssid"])] = {
                "ssid": ssid, "bssid": ap["bssid"], "channel": ap.get("channel"),
                "signal": ap.get("signal"),
            }
        return sorted(seen.values(), key=lambda a: a["signal"] or -999, reverse=True)
    except Exception:
        return []


def snapshot():
    return {
        "pineapple": pineapple_snapshot(),
        "captures": recent_captures(),
        "baseline": load_baseline(),
        "networks": known_networks(),
    }


@app.route("/")
def index():
    return render_template(
        "index.html",
        tools=load_tools(),
        links=QUICK_LINKS,
        **snapshot(),
    )


@app.route("/api/status")
def api_status():
    return jsonify(snapshot())


def exit_node_advertised():
    out = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True)
    try:
        return bool(json.loads(out.stdout)["Self"].get("ExitNodeOption"))
    except Exception:
        return False


@app.route("/widgets/exit-node")
def widget_exit_node():
    return render_template("widget_exit_node.html", enabled=exit_node_advertised())


@app.route("/widgets/exit-node/toggle", methods=["POST"])
def widget_exit_node_toggle():
    enable = "true" if request.form.get("enable") == "on" else "false"
    result = subprocess.run(
        ["sudo", "tailscale", "set", f"--advertise-exit-node={enable}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return f"Failed to toggle exit node: {result.stderr}", 500
    return ("", 204)


@app.route("/download/<when>/hash.22000")
def download_hash(when):
    """Serve a capture's crackable hash so it can be pulled onto the RTX 4080 box in
    one click. Path-traversal-safe: the resolved file MUST sit directly inside
    CAPTURES_DIR, else 404. Tailnet-only service, but validate anyway."""
    target = (CAPTURES_DIR / when / "hash.22000").resolve()
    if target.parent.parent != CAPTURES_DIR.resolve() or not target.is_file():
        abort(404)
    return send_file(target, as_attachment=True,
                     download_name=f"{when}.22000", mimetype="application/octet-stream")


@app.route("/rescan", methods=["POST"])
def rescan():
    def run():
        try:
            PineappleClient().recon_start(scan_time=25)
        except Exception:
            pass

    threading.Thread(target=run, daemon=True).start()
    return redirect("/")


@app.route("/toggle-karma", methods=["POST"])
def toggle_karma():
    enable = request.form.get("enable") == "on"
    if enable and request.form.get("confirm_karma") != "on":
        return "Refused: check the confirmation box to turn Karma on", 400
    try:
        PineappleClient().set_karma(enable)
    except Exception as e:
        return f"Failed to toggle Karma: {e}", 500
    return redirect("/")


@app.route("/stop-capture", methods=["POST"])
def stop_capture_route():
    try:
        stop_capture_and_restart_daemons()
    except Exception as e:
        return f"Failed to stop: {e}", 500
    return redirect("/")


@app.route("/capture", methods=["POST"])
def capture():
    bssids = [b.strip() for b in request.form.get("bssids", "").split(",") if b.strip()]
    channels = [c.strip() for c in request.form.get("channels", "").split(",") if c.strip()]
    duration = int(request.form.get("duration", 90))
    crack_budget = int(request.form.get("crack_budget", 600))
    use_deauth = request.form.get("use_deauth") == "on"

    if not bssids or not channels:
        return "Refused: at least one BSSID and channel are required", 400

    try:
        # validate synchronously first so bad input fails fast, before backgrounding
        validate_bssids(bssids)
        validate_channels(channels)
    except ValidationError as e:
        return f"Refused: {e}", 400

    def run():
        try:
            run_capture(bssids, channels, duration, crack_budget, use_deauth=use_deauth)
        except ValidationError:
            pass  # already validated above; defensive only

    threading.Thread(target=run, daemon=True).start()
    return redirect("/")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8454)
