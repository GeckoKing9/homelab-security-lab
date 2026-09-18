#!/usr/bin/env python3
"""Tailscale API client using an OAuth client (never expires, unlike plain
access tokens which cap at 90 days). Credentials in code-projects/.env.master
as TAILSCALE_OAUTH_CLIENT_ID / TAILSCALE_OAUTH_CLIENT_SECRET.
"""
import json
import os
import sys

import requests

API = "https://api.tailscale.com/api/v2"


class TailscaleClient:
    def __init__(self, client_id=None, client_secret=None, tailnet="-"):
        self.client_id = client_id or os.environ["TAILSCALE_OAUTH_CLIENT_ID"]
        self.client_secret = client_secret or os.environ["TAILSCALE_OAUTH_CLIENT_SECRET"]
        self.tailnet = tailnet
        self._token = None

    def _get_token(self):
        if self._token:
            return self._token
        r = requests.post(f"{API}/oauth/token", data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        })
        r.raise_for_status()
        self._token = r.json()["access_token"]
        return self._token

    def _headers(self):
        return {"Authorization": f"Bearer {self._get_token()}"}

    def devices(self):
        r = requests.get(f"{API}/tailnet/{self.tailnet}/devices", headers=self._headers())
        r.raise_for_status()
        return r.json()["devices"]

    def dns_nameservers(self):
        r = requests.get(f"{API}/tailnet/{self.tailnet}/dns/nameservers", headers=self._headers())
        r.raise_for_status()
        return r.json().get("dns", [])

    def set_dns_nameservers(self, nameservers):
        r = requests.post(f"{API}/tailnet/{self.tailnet}/dns/nameservers",
                           headers=self._headers(), json={"dns": nameservers})
        r.raise_for_status()
        return r.json()

    def dns_preferences(self):
        r = requests.get(f"{API}/tailnet/{self.tailnet}/dns/preferences", headers=self._headers())
        r.raise_for_status()
        return r.json()


def main():
    client = TailscaleClient()
    print(json.dumps({
        "nameservers": client.dns_nameservers(),
        "dns_preferences": client.dns_preferences(),
        "devices": [{"name": d["name"], "os": d["os"], "addresses": d["addresses"],
                     "lastSeen": d["lastSeen"]} for d in client.devices()],
    }, indent=2))


if __name__ == "__main__":
    sys.exit(main())
