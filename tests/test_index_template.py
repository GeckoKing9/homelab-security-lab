#!/usr/bin/env python3
"""Server-side half of the XSS fix: rendering the dashboard with a hostile SSID/BSSID (the
kind any nearby AP can broadcast) must never emit the raw payload — Jinja autoescape, the
same mode Flask uses for .html, has to neutralise it in both text cells and the data-*
attributes the row-click handler reads."""
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

REPO = Path(__file__).resolve().parent.parent
TEMPLATES = REPO / "security-hub" / "templates"

HOSTILE_SSID = "<script>alert('ssid')</script>"
HOSTILE_BSSID = '"><img src=x onerror=alert(1)>'


def render():
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "xml"]),  # matches flask.render_template
    )
    tmpl = env.get_template("index.html")
    return tmpl.render(
        tools=[],
        links=[],
        pineapple={"reachable": True, "recon_running": False, "capture_running": False,
                   "karma_enabled": False, "installed_modules": []},
        captures=[],
        baseline={"bssids": []},
        networks=[{"ssid": HOSTILE_SSID, "bssid": HOSTILE_BSSID, "channel": "6", "signal": -42}],
    )


def test_hostile_scan_data_is_escaped():
    out = render()
    # the raw attack strings must not appear verbatim anywhere
    assert HOSTILE_SSID not in out, "raw <script> SSID reached the page"
    assert HOSTILE_BSSID not in out, "raw attribute-breaking BSSID reached the page"
    assert "<script>alert(" not in out, "unescaped <script> present"
    assert "onerror=alert(1)>" not in out, "unescaped event handler present"
    # and the escaped forms must be there (proves the value rendered, just safely)
    assert "&lt;script&gt;" in out, "SSID was dropped rather than escaped"
    # the BSSID lands in data-bssid="...": its leading quote must be entity-encoded so it
    # cannot close the attribute
    assert 'data-bssid="&#34;&gt;&lt;img' in out, "data-bssid attribute not safely encoded"


if __name__ == "__main__":
    test_hostile_scan_data_is_escaped()
    print("OK — index.html server render escapes hostile SSID/BSSID")
