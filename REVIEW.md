# Review bar for this repo

Public repo. Everything here runs on my own boxes (the Pi, the VM), often as root, and often months after I wrote it.

What failure looks like here:
- An installer that half-runs and still looks done (a `|| true` eating the real error).
- A config or root-owned file rewritten with no backup, or truncated by a crash mid-write.
- A re-run that quietly undoes choices I made by hand afterwards.
- Anything personal or secret landing in this public repo (IPs beyond the LAN ranges, usernames, keys, tokens).

Skip: `writeups/` prose, `flipper/sd-card/` payload files, `docs/` unless a command in them is wrong.

Bug classes seen:
- Non-atomic config write with no backup (burp-extensions.py, Firefox policy merge, 2026-11).
- Re-run overwrote hand-set on/off flags (burp-extensions.py, 2026-11).
- Pro-only Burp extensions written into the Community config (2026-11).
- Failure hidden by `|| true` in the toolkit (2026-11).
- Unrequested whitespace change slipped into a catalog line (2026-11).
