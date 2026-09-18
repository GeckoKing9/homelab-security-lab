#!/usr/bin/env python3
"""Kills any hashcat process left running past MAX_RUNTIME_HOURS and reports it.

Exists because a manual hashcat invocation (outside handshake_capture.py's own
--runtime cap) was left running unattended for 19 hours on 2026-07-09, pegging
the Pi at 84C with sustained thermal throttling, and Beszel's CPU alert fired
but its Discord notification never arrived (stale in-memory webhook config from
before a restart) - so this doesn't rely on that alert path at all.
"""
import os
import subprocess

from common.notify import notify_all

MAX_RUNTIME_HOURS = 3
NTFY_TOPIC = "homelab-security"


def is_hashcat_invocation(cmd):
    """True only for the actual hashcat binary. Match on argv[0] (the executable)
    ONLY, never any token in the line: a shell, editor, or script that merely
    mentions 'hashcat' as an argument (e.g. `vim hashcat_watchdog.py`, or a wrapper
    `bash -c '... hashcat ...'`) has argv[0] of bash/vim/python, not hashcat, so it
    is correctly ignored. The real binary is always exec'd directly as
    'hashcat' or '/usr/bin/hashcat'. (Confirmed 2026-07-09: an any-token match
    killed the innocent parent shell during testing.)"""
    tokens = cmd.split()
    return bool(tokens) and os.path.basename(tokens[0]) == "hashcat"


def running_hashcat_procs():
    out = subprocess.run(
        ["ps", "-eo", "pid,etimes,cmd", "--no-headers"],
        capture_output=True, text=True,
    ).stdout
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3 or not is_hashcat_invocation(parts[2]):
            continue
        pid, etimes, cmd = parts
        yield int(pid), int(etimes), cmd


def main():
    max_seconds = MAX_RUNTIME_HOURS * 3600
    for pid, etimes, cmd in running_hashcat_procs():
        if etimes < max_seconds:
            continue
        subprocess.run(["kill", "-9", str(pid)])
        hours = etimes / 3600
        alert = (f"Killed hashcat PID {pid} after {hours:.1f}h (limit {MAX_RUNTIME_HOURS}h): "
                 f"{cmd[:200]}")
        notify_all(alert, "Hashcat watchdog", NTFY_TOPIC)
        print(alert)


if __name__ == "__main__":
    main()
