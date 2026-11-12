#!/usr/bin/env python3
"""Offline tests for vm/burp-extensions.py: the config merge and the BApp unpack rules.
No network: fetch() is replaced by a stub serving a fake BApp page and zip."""
import importlib.util
import io
import json
import os
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


def ext(name, uuid=None, loaded=True, path=None):
    e = {"errors": "ui", "extension_file": path or f"/x/{name}.jar", "extension_type": "java",
         "loaded": loaded, "name": name, "output": "ui"}
    if uuid:
        e.update(bapp_uuid=uuid, bapp_serial_version=1)
    return e


def test_community_config_skips_pro_only_and_drops_old_copies():
    old = {"user_options": {"extender": {"extensions": [ext("JS Miner", "pro1")]}}}
    new = [(ext("JS Miner", "pro1"), True), (ext("Hackvertor", "free1"), False)]
    names = [e["name"] for e in burpx.merge_config(old, new, community=True)["user_options"]["extender"]["extensions"]]
    assert names == ["Hackvertor"], names
    pro = burpx.merge_config(old, new, community=False)["user_options"]["extender"]["extensions"]
    assert [e["name"] for e in pro] == ["JS Miner", "Hackvertor"]


def test_rerun_keeps_the_users_on_off_and_output_choices():
    mine = dict(ext("Turbo Intruder", "t1", loaded=True), output="file")
    old = {"user_options": {"extender": {"extensions": [mine]}}}
    out = burpx.merge_config(old, [(ext("Turbo Intruder", "t1", loaded=False), False)], community=False)
    e = out["user_options"]["extender"]["extensions"][0]
    assert e["loaded"] is True and e["output"] == "file", e


def test_hand_added_jar_with_same_name_is_replaced_not_doubled():
    old = {"user_options": {"extender": {"extensions": [ext("PwnFox", path="/home/u/Downloads/PwnFox.jar")]}}}
    out = burpx.merge_config(old, [(ext("PwnFox", path="/home/u/.BurpSuite/extensions/PwnFox.jar"), False)], community=False)
    exts = out["user_options"]["extender"]["extensions"]
    assert len(exts) == 1 and exts[0]["extension_file"].endswith(".BurpSuite/extensions/PwnFox.jar"), exts


def test_merge_leaves_unmanaged_extensions_alone():
    old = {"user_options": {"extender": {"extensions": [ext("Mine", "m1", loaded=False)]}}}
    out = burpx.merge_config(old, [(ext("Hackvertor", "free1"), False)], community=False)
    assert out["user_options"]["extender"]["extensions"][0] == ext("Mine", "m1", loaded=False)
    assert old["user_options"]["extender"]["extensions"] == [ext("Mine", "m1", loaded=False)]  # input not mutated


def test_entry_point_outside_the_bapp_folder_is_refused():
    with tempfile.TemporaryDirectory() as d:
        burpx.BURP_DIR = Path(d)
        burpx.fetch = stub_fetch(bapp_zip("../../evil.jar", {"x.jar": b"j"}))
        try:
            burpx.install_bapp(UUID, True)
        except RuntimeError as e:
            assert "EntryPoint" in str(e)
        else:
            raise AssertionError("escaping EntryPoint was accepted")
        assert not (Path(d) / "bapps" / UUID).exists(), "files unpacked before the manifest was checked"


def test_upgrade_replaces_the_folder_and_reports_pro_only():
    with tempfile.TemporaryDirectory() as d:
        burpx.BURP_DIR = Path(d)
        stale = Path(d) / "bapps" / UUID / "old-1.jar"
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b"old")
        burpx.fetch = stub_fetch(bapp_zip("new-2.jar", {"new-2.jar": b"new"}, pro_only="True"))
        entry, pro_only = burpx.install_bapp(UUID, True)
        assert pro_only is True
        assert not stale.exists(), "old version's jar left behind"
        assert Path(entry["extension_file"]).read_bytes() == b"new"
        assert entry["bapp_serial_version"] == 7 and entry["name"] == "Fake"


def test_save_json_is_atomic_and_keeps_the_mode():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "UserConfigPro.json"
        p.write_text("{}")
        os.chmod(p, 0o600)
        burpx.save_json(p, {"a": 1})
        assert json.loads(p.read_text()) == {"a": 1}
        assert p.stat().st_mode & 0o777 == 0o600
        assert sorted(x.name for x in Path(d).iterdir()) == ["UserConfigPro.json"]


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
