#!/usr/bin/env python3
"""Install a curated set of Burp Suite extensions the way the BApp Store does.

Each BApp is downloaded from portswigger.net, extracted to ~/.BurpSuite/bapps/<uuid>/ and
declared in every UserConfig*.json that exists (Pro and/or Community), so Burp loads it on
its next start. Non-store jars (PwnFox) are pinned by URL and SHA-256.

Close Burp before running it: Burp keeps its user config in memory and can write it back on
exit, which would drop these entries. Re-running is safe: managed entries are refreshed but keep
your own on/off and output choices, other extensions are left alone, Pro-only BApps never go
into the Community config.

  python3 burp-extensions.py          install everything below
  python3 burp-extensions.py --list   print the list, change nothing
"""
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import sys
import urllib.request
import zipfile
from functools import partial
from pathlib import Path

BURP_DIR = Path.home() / ".BurpSuite"
STORE = "https://portswigger.net/bappstore"

# (uuid, name, loaded, why). loaded=False = installed but unticked: turn it on in
# Extensions > Installed only for the job that needs it. With all 15 on, Burp 2026.3 rates the
# total system impact High, so the on-demand ones start off.
BAPPS = [
    ("7db49799266c4f85866f54d9eab82c89", "Auth Analyzer", True, "replays requests as user B / no session: access control"),
    ("65033cbd2c344fbabe57ac060b5dd100", "Hackvertor", True, "tag-based encoding in Repeater (Academy: SQLi filter bypass via XML encoding)"),
    ("0ab7a94d8e11449daaf0fb387431225b", "JS Miner", True, "passive secrets/endpoints from JS and JSON (Pro only)"),
    ("26aaa5ded2f74beea19e2ed8345a93dd", "JWT Editor", True, "edit/sign/attack JWTs (Academy JWT labs)"),
    ("17d2949a985c4b7ca092728dba871943", "Param Miner", True, "hidden params and unkeyed headers (Academy cache poisoning labs)"),
    ("aaaa60ef945341e8a450217a54a11646", "HTTP Request Smuggler", False, "smuggling/desync probes (Academy request smuggling labs)"),
    ("9abaa233088242e8be252cd4ff534988", "Turbo Intruder", False, "high-speed/scripted requests (Academy race condition labs)"),
    ("c1d4bd60626d4178a54d36ee802cf7e8", "Server-Side Prototype Pollution Scanner", False, "SSPP detection (Academy SSPP labs)"),
    ("d3d1f3c9427e453193eb5deb3b6c115a", "AI Prompt Fuzzer", False, "prompt-injection fuzzing of LLM endpoints (basic mode needs no Burp AI)"),
    ("3123d5b5f25c4128894d97ea1acc4976", "Active Scan++", True, "extra active/passive scanner checks (Pro only)"),
    ("b324647b6efa4b6a8f346389730df160", "Copy As Python-Requests", True, "request -> python-requests code for PoC scripts"),
    ("8370c8ea741e4dbabe892a561e10544a", "Postman Burp Importer", False, "Postman collections -> Repeater tabs (grey-box API tests)"),
    ("2495f6fb364d48c3b6c984e226c02968", "Collaborator Everywhere", False, "injects OOB headers into ALL in-scope traffic: tick only when hunting blind SSRF"),
    ("c61cfa893bb14db4b01775554f7b802e", "SAML Raider", False, "SAML message editor/attacks: tick for SSO targets"),
]

# (name, url, sha256, loaded, why)
JARS = [
    ("PwnFox", "https://github.com/yeswehack/PwnFox/releases/download/v1.0.3/PwnFox.jar",
     "eddaef68aff92fd69f507497803f86ddab9727515825732248ed442da08d971e", True,
     "colours each Firefox container's traffic (pair with the PwnFox Firefox add-on)"),
]

EXT_TYPES = {"1": "java", "2": "python", "3": "ruby"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) burp-extensions.py"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def burp_running():
    me = str(os.getpid())
    for proc in Path("/proc").glob("[0-9]*/cmdline"):
        if proc.parent.name == me:
            continue
        try:
            args = proc.read_bytes().lower().split(b"\0")
        except OSError:
            continue
        if any(b"burpsuite" in a for a in args):
            return True
    return False


def entry(name, path, ext_type, loaded, uuid=None, serial=None):
    e = {"errors": "ui", "extension_file": str(path), "extension_type": ext_type,
         "loaded": loaded, "name": name, "output": "ui"}
    if uuid:
        e.update(bapp_serial_version=serial, bapp_uuid=uuid)
    return e


def install_bapp(uuid, loaded):
    """Download one BApp, unpack it into a fresh bapps/<uuid>/, return (config entry, pro_only)."""
    page = fetch(f"{STORE}/{uuid}").decode("utf-8", "replace")
    m = re.search(rf"{re.escape(STORE)}/bapps/download/{uuid}/\d+", page)
    if not m:
        raise RuntimeError("no download link on the BApp page")
    bapp = zipfile.ZipFile(io.BytesIO(fetch(m.group(0))))
    manifest = {k.strip(): v.strip() for k, v in (line.split(":", 1) for line in
                bapp.read("BappManifest.bmf").decode().splitlines() if ":" in line)}
    missing = [k for k in ("Name", "EntryPoint", "SerialVersion") if not manifest.get(k)]
    if missing:
        raise RuntimeError(f"manifest lacks {', '.join(missing)}")
    dest = BURP_DIR / "bapps" / uuid
    entry_file = (dest / manifest["EntryPoint"]).resolve()
    if not entry_file.is_relative_to(dest.resolve()):
        raise RuntimeError(f"EntryPoint {manifest['EntryPoint']!r} points outside the BApp folder")
    staging = dest.with_name(uuid + ".new")
    shutil.rmtree(staging, ignore_errors=True)
    bapp.extractall(staging)
    shutil.rmtree(dest, ignore_errors=True)  # drop the old version's files, as the store does
    staging.rename(dest)
    ext_type = EXT_TYPES.get(manifest.get("ExtensionType", "1"), "java")
    e = entry(manifest["Name"], entry_file, ext_type, loaded, uuid, int(manifest["SerialVersion"]))
    return e, manifest.get("ProOnly", "").lower() == "true"


def install_jar(name, url, sha256, loaded):
    data = fetch(url)
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        raise RuntimeError(f"sha256 mismatch: got {got}")
    dest = BURP_DIR / "extensions" / f"{name}.jar"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return entry(name, dest, "java", loaded), False


def ext_key(e):
    """BApps are matched by uuid, other jars by name (a hand-added copy is the same extension)."""
    return e.get("bapp_uuid") or e.get("name")


def merge_config(cfg, new, community):
    """Return a copy of cfg with the managed entries refreshed; keep the user's own choices."""
    old = cfg.get("user_options", {}).get("extender", {}).get("extensions", [])
    prev = {ext_key(e): e for e in old}
    managed = {ext_key(e) for e, _ in new}
    exts = [e for e in old if ext_key(e) not in managed]
    for e, pro_only in new:
        if community and pro_only:
            continue
        kept = {k: prev[ext_key(e)][k] for k in ("loaded", "output", "errors") if k in prev.get(ext_key(e), {})}
        exts.append({**e, **kept})
    opts = cfg.get("user_options", {})
    return {**cfg, "user_options": {**opts, "extender": {**opts.get("extender", {}), "extensions": exts}}}


def save_json(path, data):
    """Write via a temp file + rename so a crash never leaves Burp a truncated config."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=4))
    os.chmod(tmp, path.stat().st_mode & 0o777 if path.exists() else 0o600)
    os.replace(tmp, path)


def jython_set(cfg):
    return bool(cfg.get("user_options", {}).get("extender", {}).get("python", {}).get("location_of_jython_standalone_jar_file"))


def main():
    if "--list" in sys.argv:
        for _, name, loaded, why in BAPPS:
            print(f"{'on ' if loaded else 'off'}  {name:42} {why}")
        for name, _, _, loaded, why in JARS:
            print(f"{'on ' if loaded else 'off'}  {name:42} {why}")
        return 0
    if burp_running():
        print("Burp is running: close it first, then re-run (it can overwrite its config on exit).")
        return 1
    configs = [p for p in (BURP_DIR / "UserConfigPro.json", BURP_DIR / "UserConfigCommunity.json") if p.exists()]
    if not configs:
        print(f"No UserConfig*.json in {BURP_DIR}: start Burp once, close it, then re-run.")
        return 1

    new, failed = [], []
    jobs = [(name, partial(install_bapp, uuid, loaded)) for uuid, name, loaded, _ in BAPPS]
    jobs += [(name, partial(install_jar, name, url, sha, loaded)) for name, url, sha, loaded, _ in JARS]
    for name, job in jobs:
        try:
            new.append(job())
            print(f"ok    {name}")
        except Exception as e:  # keep going: one dead download must not block the rest
            failed.append(name)
            print(f"FAIL  {name}: {e}")

    if burp_running():  # the downloads take a while; Burp may have been started meanwhile
        print("Burp was started during the downloads: close it and re-run. No config was changed.")
        return 1
    stamp = datetime.date.today().strftime("%Y%m%d")
    for cfg_path in configs:
        try:
            cfg = json.loads(cfg_path.read_text())
        except (OSError, ValueError) as e:
            failed.append(cfg_path.name)
            print(f"FAIL  {cfg_path}: unreadable ({e}); left untouched")
            continue
        backup = cfg_path.with_name(f"{cfg_path.name}.bak-{stamp}")
        if not backup.exists():
            shutil.copy2(cfg_path, backup)
        cfg = merge_config(cfg, new, community="Community" in cfg_path.name)
        save_json(cfg_path, cfg)
        n = len(cfg["user_options"]["extender"]["extensions"])
        py = [e["name"] for e, _ in new if e["extension_type"] == "python"]
        if py and not jython_set(cfg):
            print(f"WARN  {cfg_path.name}: {', '.join(py)} need Jython (Extensions > Settings > Python environment)")
        print(f"wrote {cfg_path} ({n} extensions, backup {backup.name})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
