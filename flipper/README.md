# flipper/ — Flipper Zero SD-card staging

Everything here is meant to be **copied onto the Flipper's microSD card**. The folder
layout mirrors the SD root, so you drag the contents of `sd-card/` onto the card (or via
qFlipper's file browser) and the `_README.txt` notes land in the right folders.

## What's in here

```
sd-card/
├── _FLIPPER_CHEATSHEET.txt   master index — read first on the device
├── subghz/_README.txt        radios: gates, pagers, sensors, replay
├── infrared/_README.txt      TV-B-Gone, universal remote, IR apps
├── nfc/_README.txt           tap cards, bank-card demo, MFKey/Seader
├── lfrfid/_README.txt        125kHz fob cloning
├── ibutton/_README.txt       Dallas contact-key cloning
├── badusb/_README.txt        keyboard-injection payloads
└── apps/GPIO/_README.txt     Marauder + hardware hacking
```

These are **plain-text** on purpose: the Flipper's built-in text viewer (open the Archive /
folder icon → the folder) displays `.txt` right on the device, offline. The `_` prefix sorts
each note to the top of its folder.

## The rest of the plan

Firmware, the full 29-app install list, the flash runbook, hardware to buy, and all the
gotchas live in **`docs/flipper-reference.md`**. This folder is just the files that go on
the card.

**Status: staged, pending flash.** Nothing has been flashed yet — see the reference doc for
the step-by-step.
