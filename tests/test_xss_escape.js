#!/usr/bin/env node
// Client-side half of the XSS fix: the escapeHtml() helper that index.html runs over every
// value it drops into innerHTML (SSID, BSSID, channel, capture phase, report text) from the
// live /api/status poll. We pull the real function out of the template and exercise it, so
// this breaks if someone weakens or removes it.
'use strict';
const fs = require('fs');
const assert = require('assert');
const path = require('path');

const INDEX = path.join(__dirname, '..', 'security-hub', 'templates', 'index.html');
const html = fs.readFileSync(INDEX, 'utf8');

const m = html.match(/function escapeHtml\(s\)\s*\{[\s\S]*?\n\}/);
assert(m, 'escapeHtml() not found in index.html — the client-side XSS guard is gone');

// eval it as an expression (strict-mode eval of a declaration won't leak the name)
// eslint-disable-next-line no-eval
const escapeHtml = eval('(' + m[0] + ')');

const payloads = [
  "<script>alert(1)</script>",
  '"><img src=x onerror=alert(1)>',
  "');fillCapture('x",
  '&<>"\'',
  'MyHomeNetwork',   // benign value must survive readably
];

for (const p of payloads) {
  const out = escapeHtml(p);
  for (const ch of ['<', '>', '"', "'"]) {
    assert(!out.includes(ch), `escapeHtml left a raw ${ch} in output for input ${JSON.stringify(p)} -> ${out}`);
  }
}

// benign text is preserved (escaping, not stripping)
assert.strictEqual(escapeHtml('MyHomeNetwork'), 'MyHomeNetwork');
// & is escaped first so nothing is double-mangled
assert.strictEqual(escapeHtml('a&b'), 'a&amp;b');
// null/undefined render as empty, never the string "undefined"
assert.strictEqual(escapeHtml(null), '');
assert.strictEqual(escapeHtml(undefined), '');

console.log('OK — index.html escapeHtml neutralises hostile scan/capture values');
