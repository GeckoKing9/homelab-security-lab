import json
import os
import urllib.request


def notify_all(message, title, topic=None):
    """Discord is the only channel redteam-toolkit alerts through — the user doesn't use
    ntfy, so posting there was dead weight. `topic` is unused now, kept so call sites don't
    need to change if ntfy is ever reintroduced for something else."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return  # not configured — skip rather than error
    body = json.dumps({"content": f"**{title}**\n{message}"}).encode()
    req = urllib.request.Request(
        webhook_url, data=body,
        # Discord's API sits behind Cloudflare and 403s requests with urllib's default
        # User-Agent (found 2026-07-08) — curl worked immediately, this is the fix.
        headers={"Content-Type": "application/json", "User-Agent": "homelab-security-hub/1.0"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=5)
