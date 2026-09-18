# homelab-security-lab

A self-hosted **privacy-and-security lab** built around a headless Raspberry Pi 4 and a set of
offensive/defensive hardware, run entirely over a private mesh network. This repo is the
sanitized, public subset of a lab I build and operate myself — the parts worth showing, with
every real hostname, IP, credential, and network identifier redacted.

The lab exists to practice the full loop that shows up in real security work: **stand a service
up, expose it deliberately (never accidentally), monitor it, attack it in a bounded lab, and
prove the fix on the real path — not on paper.**

---

## ⚠️ Authorization & ethics

The offensive tooling here (`redteam-toolkit/`, `vm/`, the Pineapple/Flipper references) is built
and used **against my own network and my own hardware only**, as a home lab.

- `handshake_capture.py` **refuses to run without `--confirm-own-network`** — an explicit,
  deliberate authorization gate, by design.
- No captured data, handshakes, PCAPs, potfiles, or real BSSIDs/MACs are in this repo. Every MAC
  in documentation is the placeholder `AA:BB:CC:DD:EE:FF`.
- Attacking networks you don't own or aren't explicitly authorized to test is illegal. Don't.

This code is shared to demonstrate engineering and tradecraft, not to enable unauthorized use.

---

## Architecture at a glance

```
                     Tailnet (WireGuard mesh, no open LAN ports)
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                             │
   Raspberry Pi 4              Wi-Fi Pineapple Mk VII         Flipper Zero
   ~18 self-hosted svcs        RF / handshake capture         Sub-GHz / NFC / BadUSB
   loopback-bound + HTTPS      ──► feeds ──►  Pi GPU crack     (Momentum + Marauder)
   proxy, DNS filtering                       pipeline
        │
   Linux security VM (offensive CLI catalog, isolated)
```

**Design rules the whole lab is held to:**
- Every service binds to `127.0.0.1` and is published only via the mesh over HTTPS — being on the
  same Wi-Fi is not enough. Exactly a handful of ports are *deliberately* public, and a scheduled
  job alerts me the moment that set drifts (see `monitoring/`).
- Managed remotely to survive as a "never physically touch it again" box.
- Secrets never live in the repo. Config files here redact them; real credentials live in a
  self-hosted vault.
- A fix isn't done until it's verified on the **real external path**, not just locally.

---

## What's in here

| Area | Path | What it shows |
|---|---|---|
| **Offensive toolkit** | `redteam-toolkit/` | Pineapple↔Pi handshake→`hashcat -m 22000` pipeline, an always-on blue-team Wi-Fi monitor, Discord reporting — with a mandatory own-network authorization gate |
| **Security dashboard** | `security-hub/` | A Flask hub that catalogs the toolset and drives capture jobs from a browser; `tools.yaml` is a living inventory of the lab's offensive/defensive tooling |
| **Attack-surface monitoring** | `monitoring/` | `funnel-exposure-check.py` — detects when the set of publicly-exposed ports drifts from the intended allowlist and alerts |
| **Private networking** | `tailscale-admin/` | A thin API client over the mesh: nodes, DNS nameservers, exit-node state |
| **DNS filtering** | `unbound-pi-hole.conf` | Recursive resolver hardening in front of network-wide DNS filtering (rebind protection, private-range guards) |
| **Monitoring & alerting** | `kuma-admin/` | Socket.IO client for programmatic uptime-monitor management |
| **Physical / RF multitool** | `flipper/`, `docs/flipper-reference.md` | Flipper Zero SD-card layout and per-domain cheatsheets (Sub-GHz, NFC, RFID, IR, BadUSB) |
| **Offensive VM** | `vm/` | A reproducible Ubuntu security-VM toolkit + a CTF reference and curated tool bookmarks |
| **Reference docs** | `docs/` | The *why* behind the toolkit, the Pineapple API, and the RF gear |
| **Writeups** | `writeups/` | Short engineering narratives — the interesting bugs and the method |

---

## Writeups

- [`writeups/attack-surface-drift.md`](writeups/attack-surface-drift.md) — catching *accidental*
  public exposure automatically, and the non-deterministic-ordering bug that made the first
  version cry wolf.
- [`writeups/measure-dont-guess.md`](writeups/measure-dont-guess.md) — the operating principle
  behind the lab: verify on the real path, measure the actual signal, don't trust the obvious one.

---

*Built and operated by [@GeckoKing9](https://github.com/GeckoKing9). Sanitized for public
release — the private repo has the live configs, this one has the engineering.*
