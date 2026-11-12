#!/usr/bin/env python3
"""Offline tests for vm/burp-extensions.py and the Firefox policy merge in Phase 5b of
vm/vm-security-toolkit.sh. No network: fetch() is replaced by a stub serving a fake BApp."""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("burpx", REPO / "vm" / "burp-extensions.py")
burpx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(burpx)

UUID = "0" * 32


def bapp_zip(entry_point, files, pro_only="False"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("BappManifest.bmf", f"Uuid: {UUID}\nName: Fake\nEntryPoint: {entry_point}\n"
                                       f"SerialVersion: 7\nExtensionType: 1\nProOnly: {pro_only}\n")
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


def stub_fetch(zip_bytes):
    page = f'<a href="{burpx.STORE}/bapps/download/{UUID}/7">Download</a>'.encode()
    return lambda url: zip_bytes if "/download/" in url else page


@contextlib.contextmanager
def patched(**attrs):
    """Temporarily replace module globals (BURP_DIR, fetch, BAPPS, ...) and always put them back."""
    saved = {k: getattr(burpx, k) for k in attrs}
    for k, v in attrs.items():
        setattr(burpx, k, v)
    try:
        yield
    finally:
        for k, v in saved.items():
            setattr(burpx, k, v)


def ext(name, uuid=None, loaded=True, path=None):
    e = {"errors": "ui", "extension_file": path or f"/x/{name}.jar", "extension_type": "java",
         "loaded": loaded, "name": name, "output": "ui"}
    if uuid:
        e.update(bapp_uuid=uuid, bapp_serial_version=1)
    return e


def cfg_with(*exts):
    return {"user_options": {"extender": {"extensions": list(exts)}}}


def exts_of(cfg):
    return cfg["user_options"]["extender"]["extensions"]


# ---- merge_config ---------------------------------------------------------------------------

def test_community_config_skips_pro_only_and_drops_old_copies():
    old = cfg_with(ext("JS Miner", "pro1"))
    new = [(ext("JS Miner", "pro1"), True), (ext("Hackvertor", "free1"), False)]
    assert [e["name"] for e in exts_of(burpx.merge_config(old, new, community=True))] == ["Hackvertor"]
    assert [e["name"] for e in exts_of(burpx.merge_config(old, new, community=False))] == ["JS Miner", "Hackvertor"]


def test_rerun_keeps_the_users_on_off_and_output_choices():
    old = cfg_with(dict(ext("Turbo Intruder", "t1", loaded=True), output="file"))
    e = exts_of(burpx.merge_config(old, [(ext("Turbo Intruder", "t1", loaded=False), False)], community=False))[0]
    assert e["loaded"] is True and e["output"] == "file", e


def test_hand_added_jar_with_same_name_is_replaced_not_doubled():
    old = cfg_with(ext("PwnFox", path="/home/u/Downloads/PwnFox.jar", loaded=False))
    out = exts_of(burpx.merge_config(old, [(ext("PwnFox", path="/b/extensions/PwnFox.jar"), False)], community=False))
    assert len(out) == 1 and out[0]["extension_file"] == "/b/extensions/PwnFox.jar" and out[0]["loaded"] is False, out


def test_renamed_entry_for_the_same_jar_file_is_replaced_not_doubled():
    old = cfg_with(ext("PwnFox v1.0.3", path="/b/extensions/PwnFox.jar", loaded=False))
    out = exts_of(burpx.merge_config(old, [(ext("PwnFox", path="/b/extensions/PwnFox.jar"), False)], community=False))
    assert len(out) == 1 and out[0]["loaded"] is False, out


def test_merge_leaves_unmanaged_extensions_alone_and_does_not_mutate_input():
    old = cfg_with(ext("Mine", "m1", loaded=False))
    out = burpx.merge_config(old, [(ext("Hackvertor", "free1"), False)], community=False)
    assert exts_of(out)[0] == ext("Mine", "m1", loaded=False)
    assert exts_of(old) == [ext("Mine", "m1", loaded=False)]


def test_config_with_unexpected_structure_is_refused():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "UserConfigPro.json"
        for bad in ('{"user_options": []}', '{"user_options": {"extender": {"extensions": {}}}}', "[]", "not json"):
            p.write_text(bad)
            try:
                burpx.load_config(p)
            except ValueError:
                continue
            raise AssertionError(f"accepted {bad}")


# ---- download_bapp / swap_in -----------------------------------------------------------------

def test_entry_point_outside_the_folder_or_missing_from_zip_is_refused():
    with tempfile.TemporaryDirectory() as d:
        for ep, files in (("../../evil.jar", {"../../evil.jar": b"j"}), ("missing.jar", {"x.jar": b"j"}), (".", {"x.jar": b"j"})):
            with patched(BURP_DIR=Path(d), fetch=stub_fetch(bapp_zip(ep, files))):
                try:
                    burpx.download_bapp(UUID, True)
                except RuntimeError as e:
                    assert "EntryPoint" in str(e), e
                else:
                    raise AssertionError(f"EntryPoint {ep!r} was accepted")
        assert not (Path(d) / "bapps").exists(), "files unpacked before the manifest was checked"


def test_download_only_stages_and_swap_replaces_the_old_version():
    with tempfile.TemporaryDirectory() as d:
        stale = Path(d) / "bapps" / UUID / "old-1.jar"
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b"old")
        with patched(BURP_DIR=Path(d), fetch=stub_fetch(bapp_zip("new-2.jar", {"new-2.jar": b"new"}, pro_only="True"))):
            e, pro_only, staging, dest = burpx.download_bapp(UUID, True)
        assert pro_only is True and stale.exists(), "download touched the live folder"
        burpx.swap_in(staging, dest)
        assert not stale.exists() and Path(e["extension_file"]).read_bytes() == b"new"
        assert sorted(p.name for p in (Path(d) / "bapps").iterdir()) == [UUID], "staging or .old left behind"


def test_failed_swap_restores_the_previous_version():
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "bapps" / UUID
        dest.mkdir(parents=True)
        (dest / "old-1.jar").write_bytes(b"old")
        missing_staging = dest.with_name(UUID + ".new")  # rename of a missing dir raises
        try:
            burpx.swap_in(missing_staging, dest)
        except OSError:
            pass
        else:
            raise AssertionError("swap of a missing staging dir did not raise")
        assert (dest / "old-1.jar").read_bytes() == b"old"


def test_burp_process_match_ignores_paths_under_dot_burpsuite():
    yes = [b"/opt/burp/burpsuite_pro.jar", b"burpsuite_community.jar", b"/home/u/BurpSuiteCommunity/BurpSuite", b"/usr/local/bin/burpsuite"]
    no = [b"/home/u/.BurpSuite/UserConfigPro.json", b"/home/u/.BurpSuite", b"burp-extensions.py", b"nano", b""]
    assert all(burpx.is_burp_arg(a) for a in yes) and not any(burpx.is_burp_arg(a) for a in no)


# ---- main() ----------------------------------------------------------------------------------

def run_main(d, running):
    calls = iter(running)
    with patched(BURP_DIR=Path(d), fetch=stub_fetch(bapp_zip("new-2.jar", {"new-2.jar": b"new"})),
                 BAPPS=[(UUID, "Fake", True, "")], JARS=[], burp_running=lambda: next(calls)), \
            contextlib.redirect_stdout(io.StringIO()):
        return burpx.main()


def seed_burp_dir(d):
    old = Path(d) / "bapps" / UUID / "old-1.jar"
    old.parent.mkdir(parents=True)
    old.write_bytes(b"old")
    cfg = Path(d) / "UserConfigPro.json"
    cfg.write_text(json.dumps(cfg_with(ext("Fake", UUID, loaded=False, path=str(old)))))
    os.chmod(cfg, 0o600)
    return old, cfg


def test_burp_started_during_downloads_changes_nothing():
    with tempfile.TemporaryDirectory() as d:
        old, cfg = seed_burp_dir(d)
        before = cfg.read_text()
        assert run_main(d, [False, True]) == 1
        assert old.read_bytes() == b"old" and cfg.read_text() == before
        assert sorted(p.name for p in (Path(d) / "bapps").iterdir()) == [UUID], "staging left behind"


def test_unreadable_config_changes_nothing():
    with tempfile.TemporaryDirectory() as d:
        old, cfg = seed_burp_dir(d)
        (Path(d) / "UserConfigCommunity.json").write_text("{broken")
        assert run_main(d, [False, False]) == 1
        assert old.read_bytes() == b"old" and "old-1.jar" in cfg.read_text()


def test_full_run_installs_keeps_choice_and_backs_up():
    with tempfile.TemporaryDirectory() as d:
        old, cfg = seed_burp_dir(d)
        assert run_main(d, [False, False]) == 0
        e = exts_of(json.loads(cfg.read_text()))[0]
        assert e["extension_file"].endswith("new-2.jar") and e["loaded"] is False, e
        assert cfg.stat().st_mode & 0o777 == 0o600
        assert any(p.name.startswith("UserConfigPro.json.bak-") for p in Path(d).iterdir())


def test_save_json_writes_through_a_symlink_and_keeps_the_mode():
    with tempfile.TemporaryDirectory() as d:
        real = Path(d) / "dotfiles" / "UserConfigPro.json"
        real.parent.mkdir()
        real.write_text("{}")
        os.chmod(real, 0o600)
        link = Path(d) / "UserConfigPro.json"
        link.symlink_to(real)
        burpx.save_json(link, {"a": 1})
        assert link.is_symlink() and json.loads(real.read_text()) == {"a": 1}
        assert real.stat().st_mode & 0o777 == 0o600
        assert sorted(p.name for p in real.parent.iterdir()) == ["UserConfigPro.json"]


# ---- Firefox policy merge (the heredoc in Phase 5b) -------------------------------------------

def run_policy_merge(path):
    sh = (REPO / "vm" / "vm-security-toolkit.sh").read_text()
    code = sh.split("<<'PY' || PHASE_FAILS", 1)[1].split("\n", 1)[1].split("\nPY\n", 1)[0]
    code = code.replace('p = "/etc/firefox/policies/policies.json"', f"p = {str(path)!r}")
    return subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)


def test_policy_merge_refreshes_kit_entries_keeps_hand_set_ones_and_backs_up():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "policies.json"
        p.write_text(json.dumps({"policies": {"ExtensionSettings": {
            "PwnFox@bi.tk": {"installation_mode": "normal_installed", "install_url": "https://stale.example/x.xpi"},
            "wappalyzer@crunchlabz.com": {"installation_mode": "blocked"}}}}))
        r = run_policy_merge(p)
        assert r.returncode == 0, r.stderr
        ext = json.loads(p.read_text())["policies"]["ExtensionSettings"]
        assert ext["PwnFox@bi.tk"]["install_url"].endswith("/pwnfox/latest.xpi")
        assert ext["wappalyzer@crunchlabz.com"] == {"installation_mode": "blocked"}
        assert len(ext) == 10 and ext["*"] == {"installation_mode": "allowed"}
        assert any(x.name.startswith("policies.json.bak-") for x in Path(d).iterdir())
        assert p.stat().st_mode & 0o777 == 0o644


def test_policy_merge_leaves_a_broken_file_untouched():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "policies.json"
        p.write_text("{broken")
        r = run_policy_merge(p)
        assert r.returncode != 0 and "NOT changed" in r.stderr, (r.returncode, r.stderr)
        assert p.read_text() == "{broken"


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok    {name}")
            except Exception as e:
                failed += 1
                print(f"FAIL  {name}: {type(e).__name__}: {e}")
    sys.exit(1 if failed else 0)
