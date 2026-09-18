# tailscale-admin

Tailscale API helper for the homelab tailnet. Lets me make DNS / device / route
changes via the API instead of walking through the admin console by hand.

## Auth

Uses an **OAuth client** (not a plain access token — those cap at 90 days). Credentials live in
`code-projects/.env.master`:

```
TAILSCALE_OAUTH_CLIENT_ID=...
TAILSCALE_OAUTH_CLIENT_SECRET=...
```

The client never expires; the helper exchanges it for a short-lived bearer token on each run.
Regenerate at https://login.tailscale.com/admin/settings/oauth if ever revoked.

## Usage

```bash
export TAILSCALE_OAUTH_CLIENT_ID=...  TAILSCALE_OAUTH_CLIENT_SECRET=...
python3 tailscale_client.py          # dumps nameservers, DNS prefs, and all devices
```

Programmatic:

```python
from tailscale_client import TailscaleClient
c = TailscaleClient()
c.dns_nameservers()             # ['100.64.0.10']  (Pi-hole)
c.dns_preferences()             # {'magicDNS': True}
c.devices()                     # list of tailnet devices
c.set_dns_nameservers([...])    # push global nameservers
```

## Notes

- **"Override local DNS"** (the toggle that forces every device onto the global nameserver) is
  NOT exposed in the public API — it stays a console-only setting. This helper sets the nameserver
  list; the override toggle is flipped by hand at https://login.tailscale.com/admin/dns.
- Pi-hole answering tailnet peers requires `dns.listeningMode = ALL` on the Pi — see the project
  documented gotcha. Setting the nameserver here without that returns SERVFAIL for every peer.
