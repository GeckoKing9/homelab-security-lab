# WiFi Pineapple Mark VII — Reference

Hak5 **WiFi Pineapple Mark VII** (standard, **2.4 GHz only** — `fiveGhz:false`), MediaTek MT7628AN.
Acquired 2026-07-06. Owned by the user for **authorized WiFi testing of their own network only**.
This device lives in the same project as the Pi homelab — everything Pi/Pineapple is managed from
this folder.

> Credentials are **redacted** here (repo policy: never in plaintext). Vaultwarden (`:8444`) now has
> a real account (created 2026-07-07) and the Pineapple **root/UI password + the CD AP password are
> stored in it**; home-WiFi uplink creds are user-held. The vault's master password is held
> offline. The Management-AP `CD` was reset + disabled 2026-07-07 (new password is in the vault).
> The root/UI password lives only in `~/tools/redteam-toolkit/.env` on the Pi (gitignored, never
> committed) and is read from there at runtime.

## Hardware / ports (the part that confused setup)
- Single **USB-C** = **power AND data** (built-in USB-Ethernet gadget, ASIX AX88772C). Plug it into
  a computer's USB port and it powers up *and* presents a network interface.
- The **USB-A** port is a **host** port (for an extra radio / USB storage), **not** management.
- Wall power alone = booted but unreachable. Needs USB-C→computer, or the Management AP (below).
- Draws ~2A. A Pi4 USB port can't reliably power it — use a **powered USB hub** if tethering to the Pi.

## Radios
- `wlan0` — onboard management radio (MAC `AA:BB:CC:DD:EE:FF`)
- `wlan1` → `wlan1mon` — dedicated **PineAP / monitor** radio
- `wlan2` — **internet uplink** (client mode), currently joined to the home WiFi
- `br-lan` = `172.16.42.1/24` (management LAN over USB)

## How to reach it (two paths)
1. **Direct on the LAN (preferred):** `wlan2` client mode is connected to the home WiFi, so the
   device is on the LAN at **`192.168.1.50:1471`** (DHCP — may change; rescan if it moves). The
   management UI is reachable from the LAN, so **WSL/this environment can hit it directly** with
   native `curl` — no Windows needed.
2. **USB management net:** when USB-C is plugged into the Windows PC, it's always at
   **`172.16.42.1:1471`**. From WSL (NAT mode) that address is only reachable via **Windows interop**
   (`curl.exe`, `powershell.exe` run in the Windows network namespace). Windows adapter "Ethernet 6"
   gets `172.16.42.114`.

## API cheatsheet
- Auth: `POST /api/login` with `{"username":"root","password":"<from ~/tools/redteam-toolkit/.env
  on the Pi>"}` → returns `{"token": "..."}`. Pass it as header `Authorization: <token>` on every
  call. Token is long-lived (expiry 2031, confirmed 2026-07-08 — not 2027 as originally noted).
- The UI is an Angular SPA; endpoint list is inside the gzip'd `main.*.js` bundle
  (`zcat`, then `grep -oE '/api/[a-zA-Z0-9_/{}$.:-]+'`).
- Useful endpoints:
  - `GET  /api/dashboard/cards` — CPU/mem/disk/temp, SSIDs seen
  - `GET  /api/settings/developer/dinfo` — hardware info
  - `GET  /api/settings/networking/interfaces` — all interface IPs
  - `POST /api/settings/networking/clientmode/scan` — body `{"interface":"wlan2"}` (run **twice**;
    first pass often returns `{"error":"no scan results"}` while the radio warms up)
  - `POST /api/settings/networking/clientmode/connect` — body
    `{"ssid","bssid","password","encryption","hidden","interface":"wlan2"}`
  - `GET  /api/settings/networking/clientmode/status` — connection + IP
  - `GET  /api/helpers/checkonline` — `{"online":true/false}`
  - `GET/PUT /api/settings/networking/ap/management` — Management AP; **PUT needs**
    `{"ssid","bssid","password","confirm_password","hidden","enabled"}` (both password fields must match,
    and `bssid` must be present or it 500s)
  - `GET  /api/pineap/settings`, `/api/recon/*`, `/api/modules/*` — PineAP / recon / modules

### Confirmed live 2026-07-08 (was previously unverified — `redteam-toolkit` code fixed to match)
- `GET /api/recon/scans` → `[{"scan_id","date"}, ...]`, most recent **last**, session index only —
  it does NOT contain AP data itself.
- `GET /api/recon/scans/{id}` → `{"APResults": [{"ssid","bssid","channel","signal","encryption",
  "hidden","wps","clients","num_clients", ...}]}` — the actual AP list for that scan session.
- `POST /api/recon/start` — body `{"live":false,"autoHandshake":false,"scan_time":30,"band":"0"}`
  (`band:"0"` = 2.4GHz, the only band this hardware has).
- `GET /api/pineap/settings` → `{"mode":"advanced","settings":{...,"karma":false,...}}`. To toggle
  Karma: fetch this, flip `settings.karma`, `PUT /api/pineap/settings` with the **whole**
  `{"mode","settings"}` object back (partial updates aren't supported — send everything).
- `GET /api/modules` — installed infusions. `GET /api/modules/available` — the Hak5 catalog.
  `PUT /api/modules/install` — body `{"moduleName":"<name>"}` → `{"installed":true}`.
- **Evil Portal is a Module/Infusion (`evilportal`, already installed), not a core-firmware
  toggle** — earlier notes in this repo assumed it was built-in; it isn't. Same for Karma-adjacent
  captive-portal/deauth-GUI/DNS-spoof features — they're all separate infusions. Full curated list
  installed 2026-07-08 (hcxdumptool GUI, mdk4, DNSspoof, nmap, tcpdump, httpeek, ProxyHelper2,
  cabinet, MACInfo, DenyIP, wigle) — see `docs/security-toolkit.md` and `security-hub/tools.yaml`
  for what each one does and where. Deliberately skipped: `wpasec` (uploads captured hashes to a
  third-party cracking service — never do this with anyone else's captures), `mtr` (low value).

## Current config (as of 2026-07-06 first setup)
- **Internet uplink:** `wlan2` connected to home WiFi `MyHomeNetwork` → LAN IP `192.168.1.50`,
  `checkonline` = online.
- **Management AP:** SSID `CD`, WPA2. **DISABLED 2026-07-07** — it was a redundant broadcasting
  admin plane while the Pineapple lives on home WiFi at `.187`, so it was turned off to shrink the
  attack surface. Its password was reset to a new value and given to the user directly. Re-enable
  via `PUT /api/settings/networking/ap/management` with `enabled:true` (needs `bssid`
  `AA:BB:CC:DD:EE:FF` + matching `password`/`confirm_password`) if the box ever goes mobile.
- **PineAP:** enabled + autostart, channel 11, **karma off** (deliberately — see authorization
  boundary below), SSID + handshake capture on, logging on.
- **Recon:** idle between runs; the blue-team monitor (`redteam-toolkit/wifi_blueteam_monitor.py`,
  systemd timer every 10 min) now triggers a 30s scan each cycle. Hostname `mk7`.
- **Installed infusions (2026-07-08):** evilportal, locate (pre-existing) + hcxdumptool GUI, mdk4,
  DNSspoof, nmap, tcpdump, httpeek, ProxyHelper2, cabinet, MACInfo, DenyIP, wigle (added). See
  `security-hub/tools.yaml` for what each does.
- **Firmware:** version not cleanly readable via API; **not** flashed automatically (a firmware
  update reboots the device — do it deliberately from the UI or on explicit request, ideally while
  USB-tethered so `172.16.42.1` survives the reboot).

## Authorization boundary (important)
Deauth, karma/evil-AP, evil portal, and handshake capture **transmit into the real airspace**
around the device and require an explicit go-ahead each time — `handshake_capture.py` enforces
this with a mandatory `--confirm-own-network` flag / checkbox.

**Refined 2026-07-08:** recon-only passive-style scanning (channel-hopping AP/client discovery, no
deauth/karma/handshake capture involved) is treated as a **standing authorized activity** — it's
the same low-impact site-survey behavior every phone/laptop does in the background, doesn't
associate with or disrupt anyone's devices, and is the entire basis of the always-on WiFi
blue-team monitor. Karma specifically stays off by default even though it's a one-API-call toggle,
because unlike a scoped deauth/capture against a *named* target, Karma responds to **any** nearby
device's probe requests indiscriminately — enable it deliberately, per session, not as a standing
default.
