#!/usr/bin/env python3
import json
import os
import sys
import time

import socketio


class KumaClient:
    """Kuma has no REST API for mutations — everything goes through Socket.IO events.
    Confirmed 2026-07-09: 'login', 'add' (new monitor), and the pushed 'monitorList'/
    'notificationList' events are enough for the admin tasks this project needs. Credentials
    come from ~/.homelab-creds.env (KUMA_URL/KUMA_USER/KUMA_PASS) — see that file's own
    comment for why it exists and where the equivalent Pineapple credential lives.
    """

    def __init__(self, url=None, username=None, password=None):
        self.url = url or os.environ["KUMA_URL"]
        self.username = username or os.environ["KUMA_USER"]
        self.password = password or os.environ["KUMA_PASS"]
        self.sio = socketio.Client()
        self.state = {}
        self.sio.on("monitorList", lambda d: self.state.__setitem__("monitors", d))
        self.sio.on("notificationList", lambda d: self.state.__setitem__("notifications", d))

    def connect(self, timeout=30):
        """Attend les reponses de Kuma, ne les suppose pas.

        Ce connect() dormait 2 secondes fixes puis testait le callback de login. Sur
        un Pi occupe c'est trop court : le 2026-09-02, pendant que treize conteneurs
        redemarraient, le login a repondu apres le sleep et l'appelant a lu
        `Kuma login failed: {}` — un callback vide, pas un refus. Consequence en
        cascade : palkuma a conclu "aucun moniteur", palgame n'a rien repris, et
        sept moniteurs du stack media sont restes en pause, invisibles, jusqu'a ce
        qu'un humain le remarque. Un client qui suppose au lieu d'attendre rend
        toute la supervision silencieusement fausse.

        On attend donc reellement : le callback de login, puis le push monitorList
        que tout appelant utilise juste apres.
        """
        self.sio.connect(self.url, socketio_path="/socket.io")
        result = {}
        self.sio.emit("login", {"username": self.username, "password": self.password, "token": ""},
                       callback=lambda r: result.update(res=r))
        fin = time.time() + timeout
        while "res" not in result and time.time() < fin:
            time.sleep(0.2)
        if not result.get("res", {}).get("ok"):
            raise RuntimeError(f"Kuma login failed after {timeout}s: {result}")
        # monitorList arrive juste apres le login, mais pas instantanement.
        while not self.state.get("monitors") and time.time() < fin:
            time.sleep(0.2)
        return self

    def disconnect(self):
        self.sio.disconnect()

    def monitors(self):
        return self.state.get("monitors", {})

    def notifications(self):
        return self.state.get("notifications", [])

    def edit_monitor(self, monitor_id, **changes):
        """Kuma's 'editMonitor' takes the WHOLE monitor object, not a patch — anything you
        leave out is written back as null/default. So always start from the live object the
        server pushed in monitorList and change only the keys you mean to.

        Added 2026-08-17 to retune notification behaviour (resendInterval / maxretries /
        retryInterval) without stopping the container and editing its SQLite by hand, which
        Kuma would have overwritten from its in-memory copy anyway.
        """
        live = self.monitors().get(str(monitor_id))
        if live is None:
            return {"ok": False, "msg": f"no monitor {monitor_id}"}
        body = dict(live)
        body.update(changes)
        result = {}
        self.sio.emit("editMonitor", body, callback=lambda r: result.update(res=r))
        # 3s, not 1.5s: the callback for editMonitor genuinely takes ~2s on this Pi (it
        # restarts the monitor's check loop), and a short wait reports a false failure
        # for a save that actually succeeded.
        time.sleep(3)
        return result.get("res", {})

    def pause_monitor(self, monitor_id):
        """Suspendre un moniteur sans le supprimer.

        Necessaire des que quelque chose arrete deliberement un conteneur : sur 35
        moniteurs, 14 couvrent un service que le gestionnaire de ressources peut
        eteindre. Sans ca, chaque delestage produirait une rafale de DOWN pour des
        services qui ne sont pas en panne — et un canal d'alerte qui crie pour rien
        est un canal qu'on cesse de lire.
        """
        result = {}
        self.sio.emit("pauseMonitor", int(monitor_id), callback=lambda r: result.update(res=r))
        time.sleep(2)
        return result.get("res", {})

    def resume_monitor(self, monitor_id):
        result = {}
        self.sio.emit("resumeMonitor", int(monitor_id), callback=lambda r: result.update(res=r))
        time.sleep(2)
        return result.get("res", {})

    def add_monitor(self, name, url, notification_ids=None, monitor_type="http", **overrides):
        if any(m.get("name") == name for m in self.monitors().values()):
            return {"ok": True, "msg": "already exists", "skipped": True}
        body = {
            "name": name, "description": None, "url": url, "method": "GET", "type": monitor_type,
            "active": True, "timeout": 48, "interval": 120, "retryInterval": 60,
            "resendInterval": 0, "maxretries": 2, "weight": 2000,
            "accepted_statuscodes": ["200-299"],
            "notificationIDList": notification_ids or {},
            "upsideDown": False, "ignoreTls": False, "maxredirects": 10,
            "httpBodyEncoding": "json",
        }
        body.update(overrides)
        result = {}
        self.sio.emit("add", body, callback=lambda r: result.update(res=r))
        time.sleep(2)
        return result.get("res", {})


def main():
    client = KumaClient().connect()
    print(json.dumps({
        "monitors": {mid: m["name"] for mid, m in client.monitors().items()},
        "notifications": [n["name"] for n in client.notifications()],
    }, indent=2))
    client.disconnect()


if __name__ == "__main__":
    sys.exit(main())
