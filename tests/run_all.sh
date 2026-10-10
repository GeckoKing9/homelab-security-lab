#!/usr/bin/env bash
# Run the whole test suite. No framework: each test is a standalone script that exits
# non-zero on failure. Needs python3 (with jinja2 + requests) and node on PATH.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
fail=0

run() {
  echo "=== $* ==="
  if "$@"; then echo "PASS"; else echo "FAIL"; fail=1; fi
  echo
}

run python3 "$here/test_safeparse.py"
run python3 "$here/test_tailscale_timeout.py"
run python3 "$here/test_index_template.py"
run python3 "$here/test_hub_capture_errors.py"
run python3 "$here/test_bookmarks.py"
run node "$here/test_xss_escape.js"

if [ "$fail" -eq 0 ]; then echo "ALL PASS"; else echo "SOME FAILED"; fi
exit "$fail"
