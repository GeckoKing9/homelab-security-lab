import json
import os
import urllib.request


class PineappleClient:
    """Thin client for the Pineapple Mark VII's undocumented Angular-bundle API.

    Login payload and token field confirmed 2026-07-08 against the live device
    by decompiling main.*.js: t.prototype.login builds {username, password}
    and reads response.token.
    """

    def __init__(self, host=None, password=None, username="root"):
        self.host = host or os.environ.get("PINEAPPLE_HOST", "192.168.1.50")
        self.password = password or os.environ["PINEAPPLE_ROOT_PASS"]
        self.username = username
        self.base = f"http://{self.host}:1471"
        self.token = None

    def login(self):
        body = json.dumps({"username": self.username, "password": self.password}).encode()
        req = urllib.request.Request(
            f"{self.base}/api/login", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        self.token = data["token"]
        return self.token

    def _call(self, method, path, body=None):
        if self.token is None:
            self.login()
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"{self.base}{path}", data=data,
            headers={"Content-Type": "application/json", "Authorization": self.token},
            method=method,
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())

    def recon_stop(self):
        return self._call("POST", "/api/recon/stop")

    def recon_start(self, scan_time=30, band="0"):
        body = {"live": False, "autoHandshake": False, "scan_time": scan_time, "band": band}
        return self._call("POST", "/api/recon/start", body)

    def recon_status(self):
        return self._call("GET", "/api/recon/status")

    def recon_scans(self):
        """List of past scan sessions: [{scan_id, date}, ...], most recent last."""
        return self._call("GET", "/api/recon/scans")

    def recon_scan_results(self, scan_id):
        """AP list for one scan session: {"APResults": [{ssid, bssid, channel, signal, ...}]}."""
        return self._call("GET", f"/api/recon/scans/{scan_id}").get("APResults", [])

    def handshakes_stop(self):
        return self._call("POST", "/api/pineap/handshakes/stop")

    def pineap_settings(self):
        return self._call("GET", "/api/pineap/settings")

    def set_karma(self, enabled):
        current = self.pineap_settings()
        settings = current["settings"]
        settings["karma"] = enabled
        return self._call("PUT", "/api/pineap/settings",
                           {"mode": current["mode"], "settings": settings})

    def modules_installed(self):
        return self._call("GET", "/api/modules")
