# Catching accidental public exposure

Almost everything in this lab is reachable only over the private mesh. A small, deliberate set of
ports is public. The risk isn't the ports I chose to expose — it's the one that becomes public
when I *didn't* choose it: a service that gets re-created with the wrong flag, a proxy command
that silently changes scope, a config that resets on an update.

So the intended public set is written down, and a scheduled job checks reality against it every
few hours. If the live set of publicly-served ports differs from the allowlist in either
direction — something newly exposed, or something expected that fell off — it alerts.

## The bug that made it useless at first

The first version compared the live exposure list to the expected list as raw text. It fired
constantly with false positives.

The cause: the command that reports the public serving config returns its entries in
**non-deterministic order**. Two runs, identical state, different line order — and a naive
string comparison reports "drift" every time. The alert was crying wolf, which is worse than no
alert, because you learn to ignore it.

The fix is boring and correct: **parse the entries, sort them by a stable key (the URL), then
compare.** Compare sets, not serialized text.

```python
live = sorted(parse_serve_status(),  key=lambda b: b["url"])
want = sorted(load_allowlist(),       key=lambda b: b["url"])
if live != want:
    alert(diff(want, live))
```

## Why it's in a security portfolio

This is attack-surface management in miniature. The valuable habit isn't "expose fewer things"
— it's **treating your intended exposure as a declared spec and continuously proving reality
matches it**, with an alerting path that stays trustworthy. An alert you've trained yourself to
ignore is a control you don't have.

See `monitoring/funnel-exposure-check.py`.
