"""Small, dependency-free parsing helpers for the hub.

Pulled out of app.py so the two pieces that touch untrusted/concurrent input — form
numbers and files another process is writing live — can be unit-tested without standing
up Flask or the capture toolkit.
"""
import json
from pathlib import Path


def parse_bounded_int(raw, *, default, lo, hi):
    """Parse a form field to an int inside [lo, hi].

    An empty/missing field falls back to ``default`` (the form ships defaults). Anything
    non-numeric or out of range raises ValueError so the caller can answer 400 instead of
    letting a bare ``int("x")`` surface as a 500 — and so a hand-crafted request can't ask
    for a negative or absurd duration/crack budget.
    """
    if raw is None or str(raw).strip() == "":
        return default
    try:
        val = int(str(raw).strip())
    except (TypeError, ValueError):
        raise ValueError(f"must be a whole number, got {raw!r}")
    if not (lo <= val <= hi):
        raise ValueError(f"must be between {lo} and {hi}, got {val}")
    return val


def read_json_file(path, default):
    """Read JSON from ``path``, returning ``default`` if it's missing, unreadable, or not
    valid JSON yet.

    meta.json is written live by run_capture while the dashboard polls every few seconds,
    so a half-written file is a normal, expected state — it must degrade to "no data for
    this run", never crash the whole page.
    """
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default
