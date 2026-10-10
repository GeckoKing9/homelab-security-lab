#!/usr/bin/env python3
"""The hub's /capture error responses must never be served as HTML: the message can carry a
submitted BSSID/channel/duration, and an HTML response would run it as markup in the hub's
origin. Imports the real security-hub/app.py with the out-of-repo toolkit stubbed.
Needs flask and pyyaml; prints SKIP and exits 0 when they are missing."""
import importlib.util
import sys
import types
from pathlib import Path

try:
    import flask  # noqa: F401
    import yaml  # noqa: F401
except ImportError as e:
    print(f"SKIP — test_hub_capture_errors needs flask and pyyaml ({e.name} missing)")
    sys.exit(0)

hub = Path(__file__).resolve().parent.parent / "security-hub"
sys.path.insert(0, str(hub))


class ValidationError(Exception):
    pass


def validate_bssids(bs):
    for b in bs:
        if len(b) != 12 or not all(c in "0123456789abcdefABCDEF" for c in b):
            raise ValidationError(f"'{b}' is not a valid bare-hex BSSID")


def validate_channels(cs):
    for c in cs:
        if not c.isdigit() or not 1 <= int(c) <= 196:
            raise ValidationError(f"channel {c} out of range")


toolkit = types.ModuleType("handshake_capture")
toolkit.ValidationError = ValidationError
toolkit.validate_bssids = validate_bssids
toolkit.validate_channels = validate_channels
toolkit.run_capture = lambda *a, **k: None
toolkit.stop_capture_and_restart_daemons = lambda *a, **k: None
common = types.ModuleType("common")
common.__path__ = []
pineapple = types.ModuleType("common.pineapple_client")
pineapple.PineappleClient = object
sys.modules.update({"handshake_capture": toolkit, "common": common,
                    "common.pineapple_client": pineapple})

spec = importlib.util.spec_from_file_location("hub_app", hub / "app.py")
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
client = app_module.app.test_client()

PAYLOAD = "<img src=x onerror=alert(document.domain)>"
for name, form in {
    "duration": dict(bssids="aabbccddeeff", channels="6", duration=PAYLOAD),
    "bssid": dict(bssids=PAYLOAD, channels="6", duration="90"),
    "channel": dict(bssids="aabbccddeeff", channels=PAYLOAD, duration="90"),
}.items():
    r = client.post("/capture", data=form)
    assert r.status_code == 400, (name, r.status_code)
    ctype = r.headers.get("Content-Type", "")
    assert ctype.startswith("text/plain"), f"{name}: error served as {ctype!r}"
    assert r.headers.get("X-Content-Type-Options") == "nosniff", name

ok = client.post("/capture", data=dict(bssids="aabbccddeeff", channels="6",
                                        duration="90", crack_budget="600"))
assert ok.status_code != 400, f"a valid capture request was refused ({ok.status_code})"
print("OK — /capture errors are text/plain for hostile duration, bssid and channel")
