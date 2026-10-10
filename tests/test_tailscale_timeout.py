#!/usr/bin/env python3
"""Regression test: every Tailscale API call must pass an explicit timeout, so a stalled
API can never hang the helper indefinitely. Stubs `requests` — makes no network calls."""
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tailscale-admin"))

import tailscale_client as tc


class _FakeResp:
    def raise_for_status(self):
        pass

    def json(self):
        # superset covering every call's expected shape
        return {"access_token": "tok", "devices": [], "dns": [], "magicDNS": True}


def test_all_calls_pass_timeout():
    calls = []

    def record(method):
        def _call(url, **kw):
            calls.append((method, url, kw))
            return _FakeResp()
        return _call

    # swap the module's `requests` for a stub so nothing touches the network
    tc.requests = types.SimpleNamespace(get=record("get"), post=record("post"))

    c = tc.TailscaleClient(client_id="id", client_secret="secret")
    c.devices()
    c.dns_nameservers()
    c.set_dns_nameservers(["100.64.0.10"])
    c.dns_preferences()

    assert calls, "no HTTP calls were recorded"
    # includes the OAuth token POST triggered by the first authenticated call
    assert any("oauth/token" in url for _, url, _ in calls), "token exchange never happened"
    for method, url, kw in calls:
        assert "timeout" in kw, f"{method} {url} was sent with no timeout"
        assert kw["timeout"] == tc.HTTP_TIMEOUT, f"{method} {url} used {kw['timeout']!r}, not HTTP_TIMEOUT"


if __name__ == "__main__":
    test_all_calls_pass_timeout()
    print("OK — tailscale_client every request carries HTTP_TIMEOUT")
