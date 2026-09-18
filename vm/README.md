# vm — the user's CTF/security VM: toolkit + ops reference

Canonical, version-controlled home for everything about the user's separate **Ubuntu 24.04
VMware VM** — the OSINT/CTF/pentest workstation, distinct from the Pi (the always-on homelab
appliance). The user does **not** keep working copies in Downloads — this is the source of
truth. **Before suggesting or installing any new tool, scan these files first and tell the user
if they already have something that solves the problem** (see memory
`security-toolkit-inventory.md`).

## Files

- **`ctfvm-reference.md`** — VM access (SSH alias, static IP), the NordVPN kill-switch/
  LAN-discovery gotcha, and the credential-search toolkit (`findcred`/`cleancreds`/`showdupes`)
  architecture and ops notes.
- **`cybersec-master-bookmarks.html`** — 221-tool master bookmark collection, Netscape format
  (Firefox one-click import). 4 top folders — OSINT / Red Team / Blue Team / Learn & Reference —
  with capability subfolders, emoji-free, ranked most-useful-first, plain-English descriptions.
  Import is **additive** (re-importing = duplicates). Personal login/dashboard URLs redacted for
  git (Notion workspace ID, personal course paths); the user's live browser copy still has them.
- **`build_master_bookmarks.py`** — generator for the HTML above. Full `TREE` dict of every tool +
  description; edit here and re-run to regenerate. This is the editable source; the HTML is output.
- **`vm-security-toolkit.sh`** — phased installer for the matching CLI arsenal on the VM.
  `INSTALL_HEAVY=0` toggle at top gates the big/slow installs. Also installs a permanent
  `sectools` reference command and a `newtool` bash helper (venv-per-cloned-repo, dodges
  PEP 668). Run with `--list` / `--help` for the annotated catalog without installing.

## VM context (not the Pi)

This kit lives on the user's separate **Ubuntu 24.04 VMware VM**, not the Raspberry Pi. The Pi's
own on-host security toolkit + Pineapple pairing is documented in `../docs/security-toolkit.md` and
`../docs/pineapple-reference.md` — different machine, different purpose. The VM is the OSINT/CTF/
pentest workstation; the Pi is the always-on homelab appliance.

## Open VM action

NetExec (`nxc`) needs a Rust toolchain: on the VM run
`sudo apt-get install -y cargo rustc pkg-config` then
`pipx install --force git+https://github.com/Pennyw0rth/NetExec`. impacket already works (its
commands are script-named, e.g. `secretsdump.py`, not `impacket-secretsdump`).
