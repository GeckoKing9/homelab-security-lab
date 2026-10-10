#!/usr/bin/env python3
"""Unit tests for security-hub/safeparse.py — the form-number and live-file parsing the
capture dashboard relies on. Pure stdlib, no Flask, no capture toolkit."""
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "security-hub"))

from safeparse import parse_bounded_int, read_json_file


def test_parse_bounded_int():
    # empty / missing -> default
    assert parse_bounded_int(None, default=90, lo=1, hi=3600) == 90
    assert parse_bounded_int("", default=90, lo=1, hi=3600) == 90
    assert parse_bounded_int("   ", default=90, lo=1, hi=3600) == 90
    # valid in range, with surrounding whitespace
    assert parse_bounded_int(" 120 ", default=90, lo=1, hi=3600) == 120
    assert parse_bounded_int("1", default=90, lo=1, hi=3600) == 1
    assert parse_bounded_int("3600", default=90, lo=1, hi=3600) == 3600
    # non-numeric -> ValueError (caller answers 400, not a 500)
    for bad in ["abc", "9x", "1.5", "0x10", "9 9", "ten"]:
        try:
            parse_bounded_int(bad, default=90, lo=1, hi=3600)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad!r}")
    # out of range -> ValueError (no negative/absurd captures)
    for bad in ["0", "-5", "3601", "999999"]:
        try:
            parse_bounded_int(bad, default=90, lo=1, hi=3600)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for out-of-range {bad!r}")
    # crack_budget allows 0 when lo=0
    assert parse_bounded_int("0", default=600, lo=0, hi=86400) == 0


def test_read_json_file():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        # missing file -> default
        assert read_json_file(d / "nope.json", {"x": 1}) == {"x": 1}
        # valid json
        good = d / "good.json"
        good.write_text('{"phase": "cracking", "duration": 90}')
        assert read_json_file(good, {}) == {"phase": "cracking", "duration": 90}
        # half-written / corrupt json (the live-capture race) -> default, no crash
        half = d / "half.json"
        half.write_text('{"phase": "captu')
        assert read_json_file(half, {}) == {}
        # empty file -> default
        empty = d / "empty.json"
        empty.write_text("")
        assert read_json_file(empty, {"bssids": []}) == {"bssids": []}


if __name__ == "__main__":
    test_parse_bounded_int()
    test_read_json_file()
    print("OK — safeparse (parse_bounded_int, read_json_file)")
