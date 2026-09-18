# CTF VM reference

VMware Ubuntu 24.04 VM on my Windows host, used for authorized CTF exercises (credential search
over my own leak-style dumps). Kept identity-separate from my real accounts on purpose — I never
sign into a personal service on this VM; I use SSH from a normal session instead.

## Access

- `ssh ctfvm` (alias in `~/.ssh/config`, key `~/.ssh/ctfvm_ed25519` — dedicated key, not shared
  with `homelab` or any other host).
- Static LAN IP `192.168.21.128/24` (VMware NAT, `VMnet8`, host gateway `192.168.21.1`) — pinned
  via `nmcli` so it survives reboot; was DHCP before 2026-08-01.
- User: `mdp-est-un-espace`. **Passwordless full `sudo` (`NOPASSWD: ALL`)** as of 2026-08-02
  (`/etc/sudoers.d/ctf-automation`, replaced the earlier `ip`/`nmcli`-only scope) — real root on a
  real (if disposable/anon) VM; use freely but carefully.

## NordVPN kill switch — read before touching networking on this VM

This VM runs NordVPN connected by default (OpenVPN/TCP) for anonymity during CTF work. Its kill
switch blocks **all** non-tunnel inbound/outbound traffic by default, including LAN SSH — this
looked exactly like a routing bug the first time (ARP resolves, SYN arrives per `tcpdump`, zero
reply on any interface) and took a full diagnostic pass to isolate from an actual `ip rule`
policy-routing issue that was also present at the same time.

**Fix (already applied, persists automatically):** `nordvpn set lan-discovery enable`. This is a
stored daemon setting — NordVPN regenerates its own `ip rule` entries for all RFC1918 ranges
(`10.0.0.0/8`, `172.16.0.0/12`, `192.168.1.0/16`, `169.254.0.0/16` → table `main`) and its
`nftables` `table inet nordvpn` LAN-allow rules every time it reconnects, including after a
reboot. Don't hand-edit that `nftables` table directly (`policy drop` chain named `input`/`output`
under `table inet nordvpn`) — the daemon owns it and will overwrite manual rules on next connect.

If SSH to this VM ever silently times out again while NordVPN is connected: check
`nordvpn settings | grep -i lan` first before assuming a network/routing problem.

## Credential search toolkit

**Architecture (rewritten 2026-08-02):** all four tools are standalone executables in
`~/.local/bin/` (on `PATH` via `.bashrc`), not shell functions. `~/.findcred.sh` and the inline
`findcred()`/`findcred_list()` definitions that used to live directly in `.bashrc` are fully
retired (renamed `.deprecated-see-local-bin` / deleted) — a shell function gets loaded into a
running terminal's memory once and never notices the underlying file changing, which caused the
exact same already-open-terminal-runs-stale-code crash **three times** in one session before the
whole toolkit was converted to real executables. A standalone script has no cached state to go
stale: every invocation execs fresh from disk. Scan target throughout: every `.txt` under
`~/Downloads/Telegram Desktop/` (non-recursive, `-maxdepth 1`).

**ripgrep is now a hard requirement**, not an optional fast-path. Installed as a static binary at
`~/.local/bin/rg` (musl build from GitHub releases — `sudo apt install` needs an interactive
password ripgrep didn't need to wait for). All four tools check for it and exit with a clear
error if missing, rather than silently degrading to slower `grep`.

- `findcred <term>` — `rg -F -w` (fixed-string + whole-word). Rewritten from the old hand-built
  `\bescaped-term\b` regex, which had an incomplete escape list (missing `]` and `}`) that
  silently returned zero results for any search term containing those characters — `-F` sidesteps
  the entire escaping problem by never treating any character as regex syntax.
- `findcred_list [pattern_file]` — multi-pattern search (default `~/Documents/emails.txt`).
  **Two-stage pipeline**, not a single `rg -F -w -f`: measured empirically that `rg`'s `-w`
  combined with `-f` (many patterns) falls off its fast multi-pattern path — 3+ minutes on the
  real dataset with `-w`, 7s without. Stage 1 is a fast plain `-F -f` substring pass across the
  full file; stage 2 re-checks only that small candidate output with `-F -w -f` to drop
  substring-only false positives (e.g. a longer string that happens to contain a pattern without
  being a real whole-word match). Same exact result as a single-pass `-F -w -f`, ~10x faster.
  Filters blank/whitespace-only lines and `\r` out of the pattern file first — an empty pattern
  under fixed-string matching matches every line, which would silently return the entire dataset.
- `cleancreds` — full rebuild every run, not additive. Pulls in **every** `.txt` file present,
  by name, with zero exceptions — including any existing `clean_creds.txt`, so a prior run's
  output always gets folded back in and re-deduped alongside whatever's new. Single global
  `LC_ALL=C sort -u --parallel=$(nproc) -S 2G --compress-program=zstd`, no per-file tagging
  needed (unlike `showdupes`, it doesn't need to know *which* file a line came from). Drops any
  line over 2000 bytes as malformed before sorting (see Data quality note below). Originals are
  moved to the real desktop Trash (`gio trash` — same-filesystem rename, recoverable via Thunar,
  not `rm`) only *after* the merge is written to a temp file and verified non-empty; if the
  pipeline fails for any reason, `set -e`+`pipefail` aborts before anything is touched, so a
  failed run just means "run it again" — no resume logic, no partial-state risk. Also guards
  against the folder's live nature (new Telegram downloads land in it in real time): stats every
  source file's size, waits 3s, checks again, aborts untouched if anything changed size (would
  otherwise merge-then-trash a still-downloading file, losing whatever hadn't arrived yet).
- `showdupes` — read-only, nothing written or trashed. Stats summary: files scanned, total/
  unique/duplicated line counts with %, redundant copies with %, same-file vs cross-file split.
  Unlike `cleancreds`, *does* need to track which file each line came from, which means tagging
  every line with a file-index before sorting — this went through three failure modes before
  landing on something reliable, see below.

### Data quality: malformed lines in the real dataset

Found empirically 2026-08-02: the real combo-list data contains lines up to **4.7MB** long — 138
lines over 10KB total, almost certainly corrupted/concatenated scrape artifacts (confirmed by
sampling: base64 blobs, binary garbage, no resemblance to `service:email:password`), not real
credentials. These single-handedly wrecked every search tool's performance regardless of which
grep/rg flags were used (multi-minute searches that should take seconds) and inflated `showdupes`'
resident memory. `cleancreds` now drops anything over 2000 bytes automatically (real credential
lines never come remotely close to that) — this is a permanent guard, not a one-time cleanup, so
future consolidations can't reintroduce the problem. If search performance ever tanks again
unexpectedly, check for oversized lines before assuming a tool regression:
`awk 'length($0)>10000{c++}END{print c+0}' "the file"`.

### showdupes tagging: three failure modes, in order

Building the same-file/cross-file split required tagging each line with a small integer
file-index before a single disk-backed sort, then a streaming aggregation pass (the per-line
"which files" set is local to the current content-group and cleared every time content changes,
so it's bounded by that one line's duplicate count, never by dataset size — safe without a
resident hash table). Getting the *tagging* right took three attempts against this real,
genuinely messy 157M+-line dataset:

1. **Resident `awk` hash for cross-file tracking** — fine on toy data, but on real data hit
   5.4GB RSS and drove the VM into swap thrashing (killed, not a hang).
2. **Tab as the tag separator** (`content\tfileidx`) — broke because real leak-dump lines
   sometimes contain literal tab characters, corrupting the field split into a bogus file-index
   that didn't exist (`bash: files[idx-1]: unbound variable`).
3. **A raw SOH/0x01 byte as the separator** — better, but at 157M+ lines even a control byte
   eventually collides: it didn't crash this time, it **silently produced a wrong duplicate
   count** (129 phantom duplicates on a file independently verified via `sort | uniq -dc` to have
   zero real ones). Silent wrong output is worse than a crash — this was only caught by
   cross-checking against that independent ground truth, not by the tool's own output looking
   wrong.

**Final design:** a fixed-width 5-digit zero-padded **prefix** (`printf "%05d%s", idx, $0`), sort
by character position (`sort -k1.6`, skip the first 5 chars), extract via `substr()` at fixed
character offsets rather than searching for any delimiter. This is categorically immune to the
whole bug class — extraction never depends on a byte value being absent from the data, only on
position, which is always well-defined regardless of content. A per-file breakdown (files ranked
by size with a per-file duplicate %) was attempted on top of this and dropped after it broke
twice on real-world edge cases despite two rounds of fixes — not worth chasing further once the
core summary stats were proven reliable; kept the summary, cut the extra feature.

**Scale note:** on the real dataset (1 consolidated file post-`cleancreds`, ~157.8M lines) both
`showdupes` and `cleancreds` take **~2.5-3 min**. `findcred` ~6s, `findcred_list` ~18s (both after
the malformed-line cleanup — before it, some searches took 3+ minutes on the exact same data with
identical flags, purely from the oversized-line poisoning above). If `showdupes`/`cleancreds`
ever seem stuck: `ps aux | grep sort` + `free -h` first — RSS in the low hundreds of MB to low
GB and CPU-bound is healthy and just needs the minutes; RSS climbing unbounded or swap draining
means a resident-hash-style bug came back; `df -h /` full means temp-file cleanup failed (check
for orphaned `/tmp/sort*` files, safe to delete — `sort` cleans them up itself on a normal exit
but not after `kill -9`). **Never run two of these tools concurrently** — two `sort`/`rg`
processes competing for the same RAM on this 7.7GB VM caused a real OOM kill mid-session.

Backups of every pre-rewrite version are in `~/.local/bin/*.bak-*` on the VM.

## malware-scanner (`malscan` / `detonate`): hardening pass, 2026-08-03

I built a genuinely mature static+dynamic malware triage tool
at `~/tools/malware-scanner/` (moved from `~/Desktop/malware-scanner/` — it was
`~/tools/` is this VM's convention, matching `Responder`/`spiderfoot`/
`velociraptor`). `malscan` = static triage (ClamAV/YARA/capa/FLOSS/PE analysis, never executes
anything). `detonate` = dynamic — actually runs the file in an isolated Docker+Wine sandbox
(`detonate --cloud` submits to Hybrid Analysis instead, real Windows).

**The `clamscan` cold-start tax (the main perf fix).** `clamscan` reloads its entire signature
DB from disk on *every single invocation* — measured **~8s per file, even a 5-byte file**,
unconditionally, before any fix. For a folder scan of many files this dominated total runtime.
Fixed by installing `clamav-daemon` and switching `scanner/clamav.py` to `clamdscan --fdpass`
(daemon-backed, ~7ms/file after the one-time daemon warm-up on VM boot). `--fdpass` matters:
clamd runs as the `clamav` user and can't open arbitrary files owned by another user by path —
`--fdpass` has the client open the file and hand over the already-open file descriptor instead,
sidestepping the permission problem entirely rather than fighting `AllowSupplementaryGroups`
config. Falls back to plain `clamscan` automatically (one-time-per-worker-process check) if the
daemon is ever missing or down, so this never hard-fails, just gets slow again. Also ran
`freshclam` once — the DB was >7 days stale.

**Noisy YARA rule.** The upstream `PoetRat_Python` rule's `$grammer_massacre` string matches so
broadly it trips yara-python's "too many matches" `RuntimeWarning` on unrelated files. Not a
real bug (upstream rule-quality issue), so it's suppressed at the `rules.match()` call site in
`scanner/yara_scan.py` via a scoped `warnings.filterwarnings` rather than hand-edited into a
rule file that gets overwritten on the next `git pull` of the rule sources.

**Hybrid Analysis hash-lookup enrichment (new, `scanner/hybrid_analysis.py:hash_lookup`).**
`GET /overview/{sha256}` works on a **restricted** API key (no vetting needed) — unlike
`detonate --cloud`'s `submit_file()`, which needs the vetted FULL key. If the exact file was
ever submitted by *anyone*, this returns their real dynamic-analysis verdict for free. Wired
into `malscan`'s per-file pipeline (`--no-ha-lookup` to skip) and into `risk.py`'s scoring —
weighted heavily (`threat_score * 0.7`, capped 70) since it's an *observed* real-Windows result,
not a static heuristic. Key lives in `~/.malware-scanner-creds.env` (chmod 600, sourced from
`.bashrc` — note `.bashrc`'s own interactive-shell guard means this only loads under a real
interactive terminal or `bash -ic`, not `bash -lc`/non-interactive SSH commands; that's expected,
not a bug in the setup).

**Cloud sandbox reality, confirmed empirically this session, not assumed:** every free service
that does real-Windows dynamic detonation gates it behind some identity/org vetting —
Hybrid Analysis (restricted key free, FULL key needs a vetting form that may require real
name/business per their own docs), tria.ge (free Individual tier has **no API at all**; API
needs the same vetting as HA, and the org-info form explicitly warns "applications lacking
motivation may not be approved"), Joe Sandbox Cloud Basic (registration looked vetting-free from
docs, but the actual signup showed "we are going to review your registration now" — manual
review in practice, contradicting what public docs suggested). VirusTotal's free API is
genuinely zero-vetting but isn't a real dedicated sandbox (shallow/aggregated behavior data).
**Conclusion: don't re-research this** — the only way to get real-Windows dynamic detonation
with zero vetting, ever, unlimited, is self-hosting (CAPEv2 + a real Windows VM). Deferred for
now — user is fine using HA's website manually (email-only, no vetting, real Windows) for the
rare case that actually needs it.

**Real test result, `Setup DVREMU2 Manager v1.0.0.exe`** (the R2R-scene "DVREMU2" cracked
installer, confirmed via `R2RINNO.dll` in the extracted InnoSetup payload): `malscan` scores it
100/100 malicious (YARA capability tags: `win_hook`, `escalate_priv`, `screenshot`, `keylogger`,
`win_token`; PE imports show `AdjustTokenPrivileges`/`VirtualAlloc`/`VirtualProtect` consistent
with a packer, unsigned). The HA hash-lookup independently confirms: this exact hash was already
dynamically detonated on real Windows by someone else, verdict **malicious**, threat score
51/100. Local `detonate` (Wine) on the same file: **0/100, no evasion or malice observed** — but
the raw evidence shows it self-extracted its InnoSetup payload (`ISSKINU.DLL`/`R2RINNO.dll`)
then hung for the entire timeout window and was SIGKILL'd (exit 137), never completing —
consistent with it stalling on something Wine can't fully emulate rather than genuinely being
benign. This is exactly the Wine-fidelity gap flagged before running it: static analysis +
someone else's real-Windows run both say malicious; the local Wine sandbox's "clean" result
specifically should not be trusted for this sample.
