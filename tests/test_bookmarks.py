#!/usr/bin/env python3
"""build_master_bookmarks.py must generate its output even from a clean checkout where
./out does not exist yet, and must HTML-escape titles/URLs into the Netscape file."""
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "vm" / "build_master_bookmarks.py"


def test_generates_outputs_in_fresh_dir():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        # run with cwd = fresh dir that has no ./out — the fix must create it
        res = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=str(d), capture_output=True, text=True, timeout=60,
        )
        assert res.returncode == 0, f"generator failed: {res.stderr}"
        out = d / "out"
        html = out / "cybersec-master-bookmarks.html"
        urls = out / "urls.txt"
        assert html.is_file(), "bookmarks HTML not written"
        assert urls.is_file(), "urls.txt not written"

        body = html.read_text(encoding="utf-8")
        assert body.startswith("<!DOCTYPE NETSCAPE-Bookmark-file-1>"), "not a Netscape bookmark file"
        # titles contain '&' (e.g. "Web / CTF") which must be entity-encoded, never raw
        assert "&amp;" in body, "ampersands not HTML-escaped"
        assert "<A HREF=" in body, "no bookmark anchors emitted"

        url_lines = [u for u in urls.read_text(encoding="utf-8").splitlines() if u.strip()]
        assert len(url_lines) > 100, f"suspiciously few URLs: {len(url_lines)}"
        assert all(u.startswith("http") for u in url_lines), "non-URL line in urls.txt"


if __name__ == "__main__":
    test_generates_outputs_in_fresh_dir()
    print("OK — build_master_bookmarks.py creates ./out and escapes output")
