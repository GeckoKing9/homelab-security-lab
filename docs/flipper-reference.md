# Flipper Zero — Ops Reference

Operational doc for the user's **Flipper Zero + official WiFi Devboard V1**, owned by this
folder alongside the WiFi Pineapple. This is the fast-start + runbook; the on-device help
lives in `flipper/sd-card/*` (plain-text notes that display on the Flipper itself).

**FINAL ACCEPTANCE TEST PASSED (2026-07-14, ran twice, consistent):** Momentum mntm-012 =
latest release ✅; Marauder v1.13.0 = latest ✅; firmware API 87.1, radio_alive + stack 1.20,
region CA, enclave valid; SD FAT32 ~24GB free; all 8 READMEs md5-intact (identical both passes);
182 apps across 11 categories + GPIO/ESP; key apps present (marauder, esp_flasher, totp,
ble_spam, findmy, doom); Marauder `.fap` intact; battery 100%/Health 100% (from updater). Fully
operational.

**Status (2026-07-14): Momentum LIVE + verified. On-device help deployed + verified.**
Flashed **Momentum mntm-012** (Mainline) via the web updater (`momentum-fw.dev/update`).
Verified over serial: `firmware_origin_fork=Momentum`, `firmware_version=mntm-012`, API 87.1,
radio stack 1.20. All 8 `_README.txt` cheat sheets survived byte-for-byte (md5-matched on
device). SD mounts (FAT32, ~24.8GB free). Device name changed **Whadin3n → Jiurn** (Momentum
regenerates the name on install — cosmetic). The Flipper is reachable from WSL via
`powershell.exe` driving `System.IO.Ports.SerialPort` on COM3 (set `DtrEnable=$true` or the CLI
stays silent; close qFlipper/the Momentum tab first — only one app can hold COM3).
**Marauder VERIFIED WORKING end-to-end (2026-07-14):** the WiFi Marauder app on Momentum
(`Apps → GPIO → ESP → [ESP32] WiFi Marauder → Scan → Scan AP`) scans and lists real nearby APs —
board + app + firmware all confirmed live. (App opened fine on API 87.1 despite being an old-API
build.) **Marauder flashed onto the board (2026-07-14):** ESP32-S2 devboard (MAC AA:BB:CC:DD:EE:FF,
matches its serial-# label) flashed with **Marauder v1.13.0** via esptool v4.12.0 on Windows —
`--chip esp32s2 --before no_reset --after hard_reset write_flash 0x1000 bootloader.bin 0x8000
partitions.bin 0x10000 esp32_marauder_..._flipper.bin`, hash-verified. Board was on stock Black
Magic devboard firmware before (VID 303A PID 4001, "BLACKMAGIC" — the OFW devboard fw).
**Board-flash gotchas:** native-USB S2 does NOT auto-enter download mode (esptool `default_reset`
fails "No serial data received") — must manually hold BOOT + tap RESET + release BOOT; it then
enumerates as VID 303A **PID 0002** on a new COM port (was COM6). Don't run a `chip_id` probe
first — esptool's default `--after hard_reset` kicks it back OUT of download mode; go straight to
`write_flash` with `--before no_reset`. After flashing, Marauder's flipper build shows **no USB
CDC** (talks over the GPIO UART to the Flipper, not USB) — that's normal, not a failure.
bins from Marauder release + UberGuidoZ/Marauder_BINs (bootloader/partitions).
**Remaining:** the SD's pre-existing app suite (incl. `esp32_wifi_marauder.fap`, esp_flasher,
evil_portal, ghost_esp, wardriver) was built for the OLD API 54 — may need reinstalling for
mntm-012 (API 87.1) from the app catalog.

## Hardware

- **Flipper Zero** (device name **Jiurn**, was Whadin3n on stock; hardware UID
  C15BA40027E18000) — now on **Momentum mntm-012** (API 87.1, radio stack 1.20),
  **region-provisioned CA** (Canada). On a **32GB** microSD, **FAT32**, ~29GB total / ~24.8GB
  free (swapped from 64GB on 2026-07-14). Flipper reads FAT32 or exFAT.
- **Official WiFi Devboard V1** — chip **ESP32-S2-WROVER** (label "WiFi Devboard / Model WD.1",
  FCC ID 2AC7Z-ESP32S2WROVER, confirmed from the board photos 2026-07-14). **Key limit: the
  S2 has NO Bluetooth** — WiFi (2.4GHz) only.

## Firmware decision

**→ Momentum, "mainline" release channel, flashed via the web updater / qFlipper.**

- Momentum + Official are the **only** firmwares with *signed OTA updates + rollback
  protection* — this is why we pick it over Unleashed (manual `.dfu`, no rollback) and
  RogueMaster (bleeding-edge, most bugs). The user reverted a custom firmware once before;
  the fix is **mainline channel + don't chase dev/weekly builds**.
- Update only when a feature you want lands. Mainline tracks the official firmware and is
  stable. `https://momentum-fw.dev/update` (Chrome/Edge only) or qFlipper.

## WiFi board — flash Marauder (NOT GhostESP)

GhostESP's headline features (BLE spam, AirTag spoofing, BLE detection) need **Bluetooth**,
which the S2 board **physically lacks** — so GhostESP loses its best half here. **Marauder is
the correct pick** for this board: mature, UART-native, best Flipper companion app.

**Pipeline (unchanged):** Marauder captures `.pcap` → Pi converts with `hcxpcapngtool` → crack
on the user's **Windows RTX 4080** (`hashcat -m 22000`, ~615 kH/s). The Flipper is the
*pocket* capture arm; the always-on Pineapple is the fixed one. Same authorization boundary.

Flash sources: Marauder releases `https://github.com/justcallmekoko/ESP32Marauder/releases/latest`
· easy flasher `https://github.com/SkeletonMan03/FZEasyMarauderFlash` (auto-detects the S2) ·
guide `https://github.com/justcallmekoko/ESP32Marauder/wiki/update-firmware`. Board must show as
chip type **ESP32-S2**. After first flash, the on-device **ESP Flasher** app handles updates.

## App inventory — 29 installs + built-ins

Install from the **on-device Apps catalog** (search each by name) or `lab.flipper.net` — the
catalog serves the build matching the installed firmware, which sidesteps the well-known
"random GitHub .fap won't compile" problem. For any manual `.fap`, check the last commit date;
anything untouched since 2023 will likely crash.

### Installed apps by category

| Category | Apps |
|---|---|
| **WiFi / ESP32** (GPIO) | WiFi Marauder · ESP Flasher |
| **Sub-GHz** | Spectrum Analyzer · ProtoView · Sub-GHz Bruteforcer · TouchTunes · Sub-GHz Playlist · TPMS Reader · Weather Station · POCSAG Pager |
| **NFC / RFID** | Picopass · NFC Magic · RFID/iButton Fuzzer · MFKey32 (+Nested) · Seader · Access-Control Auditor |
| **Infrared** | XRemote · IR Intervalometer |
| **Hardware / BadUSB** | UART Terminal · SPI Mem Manager · I2C Scanner · Mouse Jiggler |
| **Security** | Authenticator (TOTP) |
| **Utility** | Barcode Generator · Metronome · Morse Code |
| **Fun / Games** | Music Player · DOOM · Video Poker |

Plus **Flipper-IRDB** loaded into `/infrared/` (universal-remote code database).

### Free built-ins (ship with Momentum, no install)

TV-B-Gone · Universal Remote (TV/AC/Audio/Projector) · Sub-GHz Read/Replay + Frequency
Analyzer · NFC / RFID / iButton read+emulate+clone · BadUSB / Bad-Keyboard (QWERTY **+ AZERTY**)
· GPIO USB-UART Bridge · **BLE Spam** · BT Remote · **U2F/FIDO key** · FindMy Flipper · Wardriver
· NFC Maker.

## SD-card organization + on-device help

The card mirrors `flipper/sd-card/`. Each folder gets a `_README.txt` (sorts to top via `_`),
shown on the device via Archive → folder. Coverage:

- `_FLIPPER_CHEATSHEET.txt` — master map, fast-starts, golden rule
- `subghz/` — T-119 pagers, TouchTunes, capture+replay, fixed-vs-rolling test, Playlist, TPMS, Weather, POCSAG
- `infrared/` — TV-B-Gone, Universal Remote, Learn, XRemote, Intervalometer
- `nfc/` — read/clone, MFKey32, Seader, bank-card demo, Access-Auditor, tap-vs-fob
- `lfrfid/` — fob cloning, EM4100 vs encrypted
- `ibutton/` — Dallas key cloning
- `badusb/` — QWERTY vs AZERTY, what payloads do
- `apps/GPIO/` — Marauder attacks + UART shell / SPI dump / I2C hardware hacking

## Hardware to buy (tiny)

- **Jumper wires** (~$3) — required for UART shell / I2C / hardware hacking
- **SOIC8 test clip** (~$6, optional) — SPI firmware dumping without desoldering

## Flash runbook

0. **DONE** — 8 `_README.txt` cheat sheets pushed to the SD over serial + MD5-verified (2026-07-14).
1. **Back up** the current SD → repo/PC (the previous Downloads backup was deleted).
2. Flash **Momentum** (mainline): plug in Flipper, close qFlipper/Flipper Lab, open
   `https://momentum-fw.dev/update` in Chrome/Edge → Connect → channel **Release** → Install.
   Do not disconnect during flash.
3. Flash **Marauder** to the board: FZEasyMarauderFlash or the Marauder web flasher (Chrome/Edge),
   confirm chip = ESP32-S2, pick the devboard build.
4. Install the **29 apps** from the on-device catalog + load **Flipper-IRDB** into `/infrared/`.
5. Copy `flipper/sd-card/*` onto the SD (drag via qFlipper) so the **READMEs** land in place.
6. Live test: WiFi scan (Marauder) · one IR remote · one NFC read.
7. Add a Homepage/security-hub tile; flip this doc's status to **live**.

## Authorization boundary (same as the Pineapple)

RF-transmitting actions (deauth, Evil Portal, Sub-GHz replay/bruteforce, BadUSB, BLE spam) —
**own network / own devices, or explicit permission, each time.** Pranks are friends-only.
Passive scanning/recon is fine. **No jamming** — transmitting a jammer is illegal everywhere
(ISED Canada / FCC), regardless of target, because it bleeds into shared/licensed spectrum; the
sanctioned "knock my own devices offline" practice is **WiFi deauth** (targeted, own network).

## Gotchas — don't rediscover

- **Board is ESP32-S2 = no Bluetooth.** Don't chase GhostESP's BLE features on it. The
  Flipper's *own* BLE (BLE Spam, FindMy, BT Remote) still works — that's separate from the board.
- **Whole toolkit is 2.4GHz-only** (board + Flipper). Same 5GHz blind spot as the Pineapple/Pi.
- **Rolling code can't be cloned by replay** — apartment/building remotes are usually rolling
  (KeeLoq / Security+ / Nice FloR-S). Fixed-code (DIP switches inside, static protocol, same
  code each press) clones fine. Test with Frequency Analyzer + Read.
- **BadUSB keyboard layout must match the target PC** (QWERTY US vs AZERTY) or output is garbled.
- **Momentum: use mainline, not dev/weekly builds** — stability, and it's why the last revert
  happened. Signed OTA = clean rollback if a build misbehaves.
- **Install apps from the catalog, not random GitHub .fap** — ~41% of stale community faps don't
  compile against current firmware; the catalog build matches your firmware.
- **"Storage error: filesystem not ready" = the SD isn't mounted, not corruption.** Hit this
  2026-07-14 because the microSD was sitting in the PC's card reader, not in the Flipper. A
  reboot won't fix it (it's not a software lock); reseat/insert the card. Also: serial `storage
  write` **silently no-ops** when the FS isn't ready (reports success, stores nothing) — always
  verify writes with `storage md5 <path>` vs the local file, not just by absence of error.
- **"MPU fault / stack overflow" + boot loop right after flashing a big firmware jump is the
  RADIO CO-PROCESSOR updating, NOT a brick** (hit 2026-07-14 flashing mntm-012 over ancient
  stock 0.98.3). The Flipper's Core2 radio stack updated 1.17→1.20 as part of the install; while
  that applies you can see the crash screen and repeated reboots. **Recovery: make sure the SD is
  inserted** (the updater reads its package from the SD — if the card is out/loose it can't
  finish and keeps faulting), let it complete; it then boots clean. `qFlipper` → **Repair** is
  the fallback (reflashes firmware + radio over DFU). A boot-looping Flipper is always
  DFU-recoverable. Momentum also **regenerates the device name** on install (Whadin3n → Jiurn).
- **Serial CLI from WSL:** `powershell.exe` → `System.IO.Ports.SerialPort('COM<n>',115200)`,
  **must set `DtrEnable=$true`** or the Flipper CLI never responds. `storage write <path>` reads
  until Ctrl+C (0x03); `storage md5`/`storage read` verify. Close qFlipper first (it locks the port).
  **The COM number is NOT stable** — it was COM3 on stock, became **COM7** after the Momentum
  flash/reboots. Don't hard-code it: find the current port via `Get-PnpDevice` matching
  `VID_0483` (USB name `FLIP_<devicename>`, e.g. FLIP_JIURN).
- **Flipper is FULLY app-loaded already** (~180 apps, from the SD's pre-existing collection):
  every category populated — Tools 30 (incl. totp/barcode/qrcode/bad_kb/multi_converter),
  NFC 19 (mfkey/seader/picopass/nfc_magic/mifare_fuzzer), Sub-GHz 20 (bruteforcer/protoview/
  spectrum_analyzer/subghz_playlist/tpms/weather_station/pocsag/meal_pager=T-119), Infrared 12
  (xremote/ir_intervalometer), Games 41 (doom/videopoker/tetris/chess/…), Media 15 (music_player/
  metronome/morse_code/wav_player), Bluetooth 5 (ble_spam/findmy/hid_ble), RFID 7, iButton 3,
  USB 7 (u2f/hid), plus GPIO/ESP (marauder/esp_flasher/evil_portal/ghost_esp/wardriver). Every
  app on the curated 38 list is present + ~140 more. Apps are organized by category folder (the
  standard layout). Marauder (an old-API build) ran fine on API 87.1 → the collection is largely
  Momentum-compatible; any app that errors on open is a one-tap catalog reinstall.
- **FindMy Flipper is not a real long-term tracker** — Flipper battery ~1 day broadcasting vs an
  AirTag's ~1 year, and it ties up the device. Fine for "find my bag today"; buy an AirTag for
  set-and-forget.
