# Measure the right signal, not the obvious one

The operating principle behind this whole lab: a fix isn't done until it's verified on the real
path, and the thing you measure has to actually be the thing you care about. Two examples where
the obvious signal lied.

## "This device is bypassing the DNS filter"

Network-wide DNS filtering runs in front of every client. To check whether a specific device was
actually being filtered, I looked it up in the resolver's query log by its LAN address — and saw
**one query in 24 hours.** Obvious conclusion: it's ignoring the resolver, going straight out to
some other DNS. A hole in the filter.

Wrong. That device reaches the resolver *over the mesh*, so the resolver logs it under its **mesh
address, not its LAN address.** Under the right identity it had made over a thousand queries that
day — fully filtered. I'd measured the wrong key and nearly "fixed" a problem that didn't exist.

Lesson: when a client can appear under more than one identity (LAN IP, mesh IP, container
gateway), you have to look up **all** of them before concluding anything. The metric was fine;
the join key was wrong.

## "The local check passes, so it works"

A service can answer perfectly on `127.0.0.1` and still be broken for every real user, because
the failure lives in the layer between the outside and the loopback bind — the proxy, the DNS
name, the exposure scope. Testing locally proves the app runs. It does **not** prove the service
is reachable.

So the rule in this lab is: **verify on the real external path.** Resolve the real name, hit the
real URL from off-network, confirm the status code you expect. More than once, "fixed locally"
and "actually reachable" were two different truths — and only the second one matters.

## Why this belongs in security work

Both stories are the same failure: trusting a proxy for the truth instead of measuring the truth.
It's exactly how a control gets marked "in place" when it isn't — a firewall rule that's shadowed,
a log source that silently stopped, a scan that hit a cached response. The discipline is cheap and
it's the whole game: **measure the real signal, on the real path, under the right identity.**
