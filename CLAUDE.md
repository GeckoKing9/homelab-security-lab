# homelab-security-lab

Sanitized **public** showcase (GitHub @GeckoKing9) of a self-hosted Raspberry Pi
security lab. It holds the engineering, not the live configs — the real
configuration lives in a separate private repo, never here.

**Read first:** `README.md` — architecture, what each area does, and the design
rules the whole lab is held to. The orientation doc for any new session.

## What this repo is / isn't
- Public + sanitized: real hostnames, IPs, credentials, MACs, SSIDs are redacted
  (placeholder MAC `AA:BB:CC:DD:EE:FF`); no captured data (handshakes, PCAPs,
  potfiles, real BSSIDs) ever lands here.
- Public repo -> commit as GeckoKing9 only, never with a Claude co-author.
- `redteam-toolkit/.env.example` is the template; the real `.env` is git-ignored.

## Non-negotiable rules (from README "Design rules")
- Never weaken the authorization gate: `redteam-toolkit/handshake_capture.py` must
  refuse to run without `--confirm-own-network`.
- A fix isn't done until verified on the real external path; local success and
  reachable are two different truths.
- When upstream output order is non-deterministic, compare parsed sets, not
  serialized text (see `writeups/`).
- `security-hub` escapes untrusted scan/capture data (BSSIDs, channels, form
  values) or serves it `text/plain`, never raw HTML — DOM XSS is its recurring bug.
- Private-range CIDR is `192.168.0.0/16`; `unbound-pi-hole.conf` and the `vm/`
  docs must agree on it — a wrong or mismatched CIDR has needed correcting twice.

## Done means
- Off-hardware changes: `bash tests/run_all.sh` prints ALL PASS. No framework; each
  test is a standalone script needing python3 (jinja2 + requests) and node, and no
  test touches the real homelab or makes a network call.
- Live-path behaviour (Pi, Pineapple, Tailscale, Kuma) cannot be verified here —
  say so, don't claim it.

## Workflow (inherits code-projects/CLAUDE.md)
- Non-trivial work -> `compound-engineering:ce-work`. The group file's mandatory
  `!/security-check` + `!/code-review` gates (its full triggers, not a local
  subset) and git rules apply as written there.

## Status
- Maintained showcase, not actively built. Last work: a security-hardening pass merged as PR #1. No open milestone.
