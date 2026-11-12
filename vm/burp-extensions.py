#!/usr/bin/env python3
"""Install a curated set of Burp Suite extensions the way the BApp Store does.

Each BApp is downloaded from portswigger.net, extracted to ~/.BurpSuite/bapps/<uuid>/ and
declared in every UserConfig*.json that exists (Pro and/or Community), so Burp loads it on
its next start. Non-store jars (PwnFox) are pinned by URL and SHA-256.

Close Burp before running it: Burp keeps its user config in memory and can write it back on
exit, which would drop these entries. Re-running is safe (entries are replaced, not doubled).

  python3 burp-extensions.py          install everything below
  python3 burp-extensions.py --list   print the list, change nothing
"""
import datetime
import hashlib
import io
import json
import re
import sys
import urllib.request
import zipfile
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
    for proc in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            args = proc.read_bytes().split(b"\0")
        except OSError:
            continue
        if any(a.endswith(b".jar") and b"burpsuite" in a.lower() for a in args):
            return True
    return False


def entry(name, path, ext_type, loaded, uuid=None, serial=None):
    e = {"errors": "ui", "extension_file": str(path), "extension_type": ext_type,
         "loaded": loaded, "name": name, "output": "ui"}
    if uuid:
        e.update(bapp_serial_version=serial, bapp_uuid=uuid)
    return e


def install_bapp(uuid, loaded):
    page = fetch(f"{STORE}/{uuid}").decode("utf-8", "replace")
    m = re.search(rf"{re.escape(STORE)}/bapps/download/{uuid}/\d+", page)
    if not m:
        raise RuntimeError("no download link on the BApp page")
    bapp = zipfile.ZipFile(io.BytesIO(fetch(m.group(0))))
    manifest = dict(line.split(": ", 1) for line in bapp.read("BappManifest.bmf").decode().splitlines() if ": " in line)
    dest = BURP_DIR / "bapps" / uuid
    bapp.extractall(dest)
    ext_type = EXT_TYPES.get(manifest.get("ExtensionType", "1").strip(), "java")
    return entry(manifest["Name"].strip(), dest / manifest["EntryPoint"].strip(), ext_type, loaded,
                 uuid, int(manifest["SerialVersion"]))


def install_jar(name, url, sha256, loaded):
    data = fetch(url)
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        raise RuntimeError(f"sha256 mismatch: got {got}")
    dest = BURP_DIR / "extensions" / f"{name}.jar"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return entry(name, dest, "java", loaded)


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
    for uuid, name, loaded, _ in BAPPS:
        try:
            new.append(install_bapp(uuid, loaded))
            print(f"ok    {name}")
        except Exception as e:  # keep going: one dead download must not block the rest
            failed.append(name)
            print(f"FAIL  {name}: {e}")
    for name, url, sha, loaded, _ in JARS:
        try:
            new.append(install_jar(name, url, sha, loaded))
            print(f"ok    {name}")
        except Exception as e:
            failed.append(name)
            print(f"FAIL  {name}: {e}")

    stamp = datetime.date.today().strftime("%Y%m%d")
    for cfg_path in configs:
        backup = cfg_path.with_name(f"{cfg_path.name}.bak-{stamp}")
        if not backup.exists():
            backup.write_bytes(cfg_path.read_bytes())
        cfg = json.loads(cfg_path.read_text())
        exts = cfg.setdefault("user_options", {}).setdefault("extender", {}).setdefault("extensions", [])
        keys = {e.get("bapp_uuid") or e["extension_file"] for e in new}
        exts[:] = [e for e in exts if (e.get("bapp_uuid") or e.get("extension_file")) not in keys] + new
        cfg_path.write_text(json.dumps(cfg, indent=4))
        py = [e["name"] for e in new if e["extension_type"] == "python"]
        if py and not jython_set(cfg):
            print(f"WARN  {cfg_path.name}: {', '.join(py)} need Jython (Extensions > Settings > Python environment)")
        print(f"wrote {cfg_path} ({len(exts)} extensions, backup {backup.name})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
