# tests

Focused regression tests for the security fixes that can be verified off-hardware (no Pi,
no Pineapple, no live Tailscale/Kuma). There is no test framework — each file is a
standalone script that prints `OK` and exits `0` on success, non-zero on failure.

## Run everything

```bash
bash tests/run_all.sh
```

## Requirements

- `python3` with `jinja2` and `requests` importable (both already present on the dev box;
  `apt install python3-jinja2 python3-requests` otherwise)
- `node` (for the client-side escaping test)

No test makes a network call or touches the real homelab.

## What each covers

| File | Guards |
|------|--------|
| `test_safeparse.py` | `security-hub/safeparse.py`: bounded int parsing (bad/out-of-range capture input → 400, not 500) and tolerant JSON reads (half-written `meta.json` → no crash) |
| `test_tailscale_timeout.py` | every `tailscale_client` API call carries an explicit `HTTP_TIMEOUT` |
| `test_index_template.py` | server render of `index.html` escapes a hostile SSID/BSSID (Jinja autoescape) |
| `test_xss_escape.js` | the client-side `escapeHtml()` in `index.html` neutralises hostile `/api/status` values before `innerHTML` |
| `test_bookmarks.py` | `build_master_bookmarks.py` generates output from a clean checkout and HTML-escapes it |
