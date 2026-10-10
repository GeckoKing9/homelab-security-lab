"""Small, dependency-free parsing helpers for the hub.

Pulled out of app.py so the two pieces that touch untrusted/concurrent input — form
numbers and files another process is writing live — can be unit-tested without standing
up Flask or the capture toolkit.
"""
import json
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)
_WHOLE_NUMBER = re.compile(r"-?[0-9]+")  # ASCII digits only: no 1_0, +5 or non-ASCII numerals


def parse_bounded_int(raw, *, default, lo, hi):
    """Parse a form field to an int inside [lo, hi].

    An empty/missing field falls back to ``default`` (the form ships defaults). Anything
    non-numeric or out of range raises ValueError so the caller can answer 400 instead of
    letting a bare ``int("x")`` surface as a 500 — and so a hand-crafted request can't ask
    for a negative or absurd duration/crack budget.
    """
    if raw is None or str(raw).strip() == "":
        return default
    text = str(raw).strip()
    if not _WHOLE_NUMBER.fullmatch(text):
        # The submitted text is deliberately left out of the message: callers show it to the user.
        raise ValueError("must be a whole number")
    val = int(text)
    if not (lo <= val <= hi):
        raise ValueError(f"must be between {lo} and {hi}, got {val}")
    return val


def read_json_file(path, default):
    """Read JSON from ``path``, returning ``default`` if it's missing, unreadable, not valid
    JSON yet, or not the same kind of value as ``default`` (a ``null`` or a list where the
    caller expects an object would crash the caller's ``.get``).

    meta.json is written live by run_capture while the dashboard polls every few seconds,
    so a half-written file is a normal, expected state — it must degrade to "no data for
    this run", never crash the whole page. Anything else is logged, not swallowed.
    """
    try:
        data = json.loads(Path(path).read_text())
    except FileNotFoundError:
        return default
    except ValueError:
        log.debug("%s is not valid JSON yet (half-written?), using the default", path)
        return default
    except OSError as e:
        log.warning("cannot read %s: %s", path, e)
        return default
    if not isinstance(data, type(default)):
        log.warning("%s holds %s, expected %s; using the default", path,
                    type(data).__name__, type(default).__name__)
        return default
    return data
