# Security Toolkit — Pi + Pineapple

Installed 2026-07-07. This is the network-security tooling on the **Pi host** (apt/Metasploit repo,
plus `~/tools/Responder`), designed to pair with the WiFi Pineapple Mark VII. See
`docs/pineapple-reference.md` for the Pineapple side.

## The core architecture decision: who does what

The Pi 4's onboard WiFi chip has **no monitor mode** (supports only IBSS/managed/AP/P2P — verified
with `iw list`). So it physically cannot do live wireless capture or injection on its own radio.
That's fine — the Pineapple has purpose-built radios for exactly that. The division of labour:

- **Pineapple = capture / RF** — PineAP recon, handshake/PMKID capture, deauth, evil-portal. Only
  ever against the user's own network/devices, with an explicit per-action go-ahead (transmits into
  real airspace).
- **Pi = analysis / cracking / wired-side** — convert captures, crack, and run everything that
  doesn't need monitor mode: nmap recon, bettercap on the wired/managed side, Metasploit, tshark.

Adding a USB monitor-mode adapter to the Pi would just duplicate hardware the Pineapple already
has — not worth it. Capture on the Pineapple, pull the file to the Pi.

## What's installed (Pi host)

| Tool | Role | Notes |
|---|---|---|
| nmap | LAN discovery + service/version scan | works fully, no special hardware |
| tcpdump / tshark | packet capture/analysis on eth0 | wired side only |
| aircrack-ng | WPA handshake cracking | the `aircrack-ng` cracker works on a `.cap`; airodump/aireplay need monitor mode (Pineapple's job) |
| hcxtools | `hcxpcapngtool` pcapng→hashcat 22000, `hcxhashtool`, `hcxpsktool` | the modern conversion path |
| hcxdumptool | live capture | **non-functional here** — needs monitor mode; kept (178KB) in case a USB adapter is ever added |
| bettercap | MITM / ARP·DNS spoof / sniff / recon | wired/managed side works; its wifi module needs monitor mode |
| hashcat (+ pocl) | GPU-less cracking | pocl gives it a CPU OpenCL backend (4× Cortex-A72). **No GPU on Pi4** — light/targeted cracking only; offload big jobs to a real GPU box |
| john | password cracking | binary at `/usr/sbin/john` (added to PATH) |
| Metasploit Framework | exploitation framework | official arm64 build; `msfdb` initialized; postgres bound `127.0.0.1:5433` |
| Responder | LLMNR/NBT-NS poisoning | `~/tools/Responder`, deps in `.venv` (Debian 13 blocks system pip). Fading in effectiveness on patched Windows |
| binwalk | firmware/blob analysis | added 2026-07-08, for IoT firmware audit |
| ffuf / gobuster | web content/directory fuzzing | added 2026-07-08, for HackerOne/HTB/THM web-layer work |
| nikto | web server vuln scanner | added 2026-07-08 |
| sqlmap | SQL injection testing | added 2026-07-08 |

Wordlists: `/usr/share/wordlists/` — `rockyou.txt` (14.3M) + `OneRuleToRuleThemAll.rule` (52k rules)
+ `seclists/` (SecLists, shallow clone, ~2.5G, added 2026-07-08 for ffuf/gobuster/nikto).
`best64.rule` ships with hashcat at `/usr/share/hashcat/rules/`.

## WPA/WPA2 capture → crack pipeline

1. **Capture on the Pineapple** (Recon or PineAP → handshake/PMKID), export the `.pcapng`.
2. **Pull to the Pi**, then convert:
   ```
   hcxpcapngtool capture.pcapng -o hash.22000
   ```
3. **Crack on the Pi** (CPU — keep it targeted):
   ```
   hashcat -m 22000 hash.22000 /usr/share/wordlists/rockyou.txt \
     -r /usr/share/hashcat/rules/best64.rule
   ```
   (legacy 4-way `.cap`: `aircrack-ng -w /usr/share/wordlists/rockyou.txt capture.cap`)

Gotchas (2026): mode **22000** unifies PMKID+EAPOL (replaced 2500/16800). **WPA3-SAE is NOT
crackable this way** — no offline PMKID; only WPA2/mixed-mode yields 22000 hashes. On CPU, big
wordlists are impractical — prefer a smaller list + a good rule, or offload to a GPU machine.

**`--backend-vector-width 1` is required on this Pi for mode 22000, not optional** (found
2026-07-08): pocl's SIMD-vectorized kernel for this hash mode segfaults every hashcat worker
thread on startup on this ARM Cortex-A72 (confirmed via `strace` — `SEGV_MAPERR` the instant
threads wake from the compiled kernel; reproducible every time, mode 0/MD5 unaffected, so it's
specific to 22000's more complex kernel, not a general OpenCL/pocl breakage). It fails **silently**
under `subprocess.run` — a crashed run looks identical to a real "not cracked" result unless you
check the exit code directly (a piped `| tail` masks it too — `$?` reflects `tail`, not `hashcat`).
`redteam-toolkit/handshake_capture.py`'s `crack()` now always passes this flag; add it to any
manual `hashcat -m 22000` invocation on this box too.

**Passive PMKID capture alone doesn't always work — some routers validate the MIC before
replying** (confirmed 2026-07-08 against the user's own `MyHomeNetwork`): hcxdumptool's
rogue-client technique got real 802.11 traffic and even AP-side M1/M3 responses, but zero M2 and
zero PMKID — the router simply doesn't leak crackable material to a spoofed client. **Forcing a
real device to reconnect via deauth while hcxdumptool is already listening captures a genuine
handshake fragment from that device instead** — this is what actually worked (2 valid EAPOL pairs
written to the 22000 file, `hcxpcapngtool` reported `EAPOL M32E2 (authorized): 2`). `mdk4` (opkg
package, NOT the same as the `mdk4` Pineapple GUI infusion — that only ships the UI, the module's
own `check_dependencies`/`manage_dependencies` actions install the real binary via opkg on first
use in the UI, or just `opkg install mdk4` directly over SSH) runs fine concurrently with
hcxdumptool on the same `wlan1mon` monitor interface — no conflict, standard aircrack-ng-style
multi-process monitor sharing. `handshake_capture.py --deauth` now automates this whole sequence:
capture starts, a `mdk4 wlan1mon d -B <bssid> -c <channel> -s <pps>` burst runs partway through
(rate-limited, not a flood), then it keeps listening for the reconnection — also available as a
checkbox on the security-hub capture form. **Killing `mdk4`/`hcxdumptool` via `pkill` on the
Pineapple reliably causes a brief SSH disconnect** (same family as the daemon-restart hiccup
already documented) — reconnect and continue, it's not a real failure.

## Host posture (verified 2026-07-07)

- No offensive tool runs as a daemon; no offensive listeners. Only non-loopback listeners on the Pi
  are SSH `:22` and DNS `:53`. Metasploit's postgres is loopback-only (`127.0.0.1:5433`).
- SSH hardened: key-only + `PermitRootLogin no` + `MaxAuthTries 3` + `X11Forwarding no`
  (`/etc/ssh/sshd_config.d/99-hardening.conf`).
- **Higher-stakes note:** this box also exposes 3 public services (Ente API, PrivateBin, Ente
  albums). Co-locating offensive tooling with public exposure is an accepted-but-not-ideal pattern;
  it's kept safe by (a) nothing offensive listening, (b) not pulling untrusted payloads onto the box,
  (c) treating the Ente/Vaultwarden data as crown jewels — which is why off-device backup is the
  standing #1 priority.

## Authorization boundary

Everything that transmits (deauth, karma, handshake capture, poisoning, exploitation) is only for the
user's **own** network/devices, with an explicit go-ahead each time. This toolkit is for authorized
testing of the user's own homelab/network — not third-party targets.

## Rogue-device detection (defensive) — NetAlertX

Deployed as the one always-on defensive add (`stacks/netalertx/`). ARP-scans the eth0 LAN and pushes
new-device / device-down alerts to the ntfy topic `homelab-netalert` (separate from service-health
`homelab-alerts` to avoid alert fatigue) and, since 2026-07-08, its own dedicated Discord webhook
(`WEBHOOK` plugin enabled in `app.conf`). Two settings needed changing from their defaults:
`WEBHOOK_REQUEST_METHOD` must be `'POST'` not `'GET'` (Discord rejects GET), and
`WEBHOOK_PAYLOAD` must be `'text'` **not** `'html'` — the config file's own inline comment
recommends `'html'` for Discord, but that's wrong: a real notification (2026-07-09) showed raw
HTML tags dumped visibly into the Discord message, because Discord doesn't render HTML in that
field. The plugin's own source (`_publisher_webhook/webhook.py`) auto-detects Discord URLs and
appends `/slack` to use Discord's Slack-compatible webhook endpoint — `'text'` payload mode is
what actually renders cleanly there. Both ports loopback-only; UI via SSH forward. See the compose
file's header notes for the ntfy-port and GraphQL-bind gotchas.

## "Perfect team" buildout — 2026-07-08

Extended the toolkit to cover the full request list (handshake capture/crack, deauth-driven
capture, evil twin, MITM, WPA/WPA2 decrypt, automated recon, WPS, Karma/MANA, SSL-strip/HSTS, DNS
spoofing, IoT audit, blue+red team companions, HackerOne/HTB/THM helpers, rogue AP + client
isolation, capture automation+reporting, signal mapping). Rather than installing every named tool
verbatim, each capability was mapped to the *right* device first — several were already covered
natively and needed zero new installs.

### Capability → implementation map

| Requested capability | Where it lives | New install? |
|---|---|---|
| WPA/WPA2 handshake capture | Pineapple, `hcxdumptool` rogue-client PMKID | No — already installed |
| Deauth to force a capture | Pineapple, PineAP API | No — already installed |
| WPA/WPA2 decrypt/crack | Pi, `hcxpcapngtool` + `hashcat -m 22000` | No — already installed |
| WPS attack testing | Pineapple, `reaver` (Pixie Dust) + `pixiewps` | No — already installed |
| Evil twin / rogue AP + client isolation | Pineapple's native **Evil Portal** module | No — firmware feature, needs enabling via API, not opkg |
| Karma/MANA probe harvesting | Pineapple's native **PineAP Karma mode** | No — firmware feature, needs enabling via API, not opkg |
| MITM / SSL-strip / HSTS testing | Pi, `bettercap` (ARP-spoof on the wired/managed LAN) | No — already installed. **bettercap has no mipsel/OpenWrt build** (confirmed via GitHub releases API — linux/amd64 only), so this never belonged on the Pineapple; the Pi sits on the same LAN as the router, so wired ARP-spoof MITM against the user's own devices works without the Pineapple at all |
| DNS spoofing (sandboxed) | Pi, `stacks/dns-sandbox/` — isolated `internal: true` Docker network | New — see below |
| IoT firmware/traffic audit | Pi, `binwalk` (new) + existing `tshark`/`tcpdump` | New: `binwalk` |
| HackerOne/HTB/THM web-layer helpers | Pi: `ffuf`, `gobuster`, `nikto`, `sqlmap` + SecLists wordlists | New (all via apt + a shallow git clone) |
| Red team companion / automation + reporting | Pi, `redteam-toolkit/handshake_capture.py` | New — see below |
| Blue team companion (own WiFi) | Pi, `redteam-toolkit/wifi_blueteam_monitor.py` | New — see below |
| Automated recon dashboard | Deliberately **not** a new service — see "Considered and skipped" | N/A |
| Antenna/signal mapping | Deliberately **not built** — see "Considered and skipped" | N/A |

### `redteam-toolkit/` — capture automation + WiFi blue-team monitor

Lives at `~/tools/redteam-toolkit/` on the Pi (mirrored in this repo at `redteam-toolkit/` —
`.env` holds `PINEAPPLE_ROOT_PASS`, never committed, only `.env.example`). Full usage in its own
README. Two pieces:

- `handshake_capture.py` — one command drives the entire pipeline that used to be manual SSH:
  free the shared radio, `hcxdumptool` PMKID capture against named BSSIDs (optionally forced with
  `--deauth` via `mdk4` — see below), pull the pcapng, restart `pineapd`/`pineapple` (mandatory
  afterward, see the radio-desync gotcha in the notes), convert, crack with a time budget, write a
  report, notify to Discord. `--confirm-own-network` is required on the raw CLI; the security-hub
  web form skips this gate (self-service on the user's own gear is standing pre-authorized there).
- `wifi_blueteam_monitor.py` — systemd timer (every 10 min) polling Pineapple recon scans for the
  watched SSID, diffing seen BSSIDs against a stored baseline, alerting to Discord the moment a
  second BSSID starts broadcasting the same SSID (the evil-twin signature). This is genuinely new
  territory, not a rehash of the CrowdSec rejection below — that was about host/network intrusion
  detection blinded by Tailscale Funnel; this is RF-layer, looking at data the Pineapple already
  collects.
- **Notifications go to Discord only, not ntfy** (switched 2026-07-08 — the user doesn't use the
  ntfy app, so posting there was dead weight; `notify_all()` in `common/notify.py` posts straight
  to a Discord webhook from `DISCORD_WEBHOOK_URL` in `.env`, no-ops if unset). ntfy itself is
  unaffected and still serves Kuma/NetAlertX exactly as before — this only changed redteam-toolkit's
  own notify path. Discord's API 403s Python's default `urllib` User-Agent (behind Cloudflare) —
  a custom `User-Agent` header fixed it.

**Not yet live-verified**: the Pineapple API client's login body key and `/api/recon/scans`
response field names (`bssid`/`ssid`/`channel`) are inferred from the API notes elsewhere in this
doc, not exercised against a real response yet. Fix on first real run once the root credential is
in hand.

### DNS-spoofing sandbox (`stacks/dns-sandbox/`)

An `internal: true` Docker network (no route to the real LAN or internet, so it can never touch
the household Pi-hole even by mistake) with a `dnsmasq` answering a fake `target.lab` domain,
an "evil" and a "legit" nginx target, and a victim container to query from. `restart: "no"` on
every service — stand it up for a drill (`docker compose up -d`), tear it down after
(`docker compose down`). Verified working 2026-07-08: `nslookup target.lab 10.66.66.10` from the
victim resolves the spoofed IP; `wget -O- http://10.66.66.20/` (by IP) shows the spoofed page.
BusyBox `wget`'s own hostname resolver has a cosmetic quirk against this dnsmasq config ("bad
address" even though `getent`/`nslookup` resolve correctly) — use `nslookup` to prove resolution,
`wget`-by-IP for content. `internal: true` also means no `apk add` at runtime inside it (zero route
out) — extra debug tooling would need baking into a custom image, not installed live.

### Considered and skipped

- **Kismet as a unified recon dashboard** — the appealing idea was a single dashboard fed by both
  devices. Rejected: Kismet's *remote capture* protocol needs a capture binary running on the
  remote radio (the Pineapple), and cross-compiling/opkg-installing that onto restrictive
  mipsel/OpenWrt with a thin package feed is fragile infrastructure for a feature the Pineapple's
  own recon API + the new blue-team monitor already cover. A real Kismet deployment remains an
  option later if a dedicated monitor-mode USB adapter is ever added directly to the Pi.
- **A standing "automated recon dashboard" web service** — every prior addition to this box
  follows a hard rule of minimal new exposed surface (loopback-only backends, only :22/:53 public).
  Adding a new always-on web UI + port + Homepage tile + Kuma monitor for what's fundamentally a
  periodic-poll summary was judged not worth the surface increase; the blue-team monitor's ntfy
  alerts plus on-disk JSON/report files serve the same purpose without a new listener.
- **Signal/antenna mapping** — needs GPS to be meaningful (walk a route, plot signal strength by
  location); neither the Pi nor this Pineapple has a GPS module. Not built. Revisit if a GPS dongle
  is ever added.
- **hostapd-mana on the Pi** — the Pi has no monitor/AP-capable wireless hardware to back it (same
  constraint documented for hcxdumptool on the Pi); would be dead weight. Karma/MANA stays on the
  Pineapple's native PineAP.
- **wifite2** — still skipped, reaffirming the 2026-07-07 call: overlaps the Pineapple's own
  capture workflow, not worth the redundancy.
