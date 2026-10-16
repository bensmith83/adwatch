# Jieli "JLAISDK" self-labelled beacon (pseudo-CID 0x5401)

## Overview

A device on **Zhuhai Jieli** silicon/firmware whose main
manufacturer-data element uses an unassigned pseudo-CID instead of a SIG
company ID — the same genre as the "ZHJIELI" frame (the ZHJIELI ASCII
pseudo-CID `0x485A` spells "ZH") — and which can also send a second,
separate element under Jieli's real SIG slot `0x05D6` carrying the
AI-SDK toolchain's label "JLAISDK" ([jieli-audio.md](jieli-audio.md)
covers that slot).

One unit captured on 2026-10-09 (2 records / 7 sightings, one uploader),
nameless, co-advertising the unassigned 16-bit service UUID `0xAF30`,
emitting two frame shapes — the 20-byte `0x5401` element alone, and the
same element followed by the separate 11-byte Jieli element.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | pseudo-CID `0x5401` (wire `01 54`) | unassigned; frame bytes 1–3 spell ASCII "TBD" across the CID/payload boundary |
| Service UUID | `0xAF30` (advertised) | unassigned; 2/2 records — corroboration, not a gate |
| Jieli element | a separate manufacturer-data element under **`0x05D6` — Jieli's real SIG CID** (frame bytes 20–30 of the 31-byte shape) | the attribution |
| ASCII label | `"JLAISDK"` (JL AI SDK), inside the Jieli element (frame bytes 24–30) | part of the same element |
| Local name | none | |
| Device class | `audio` | matches `jieli_audio`'s class for the same element |

## Ad Format

### Bare variant — 20 bytes

```
01 54 | 42 44 | 02 00 20 00 60 05 00 00 0e 00 0a 00 67 00 00 00
CID     "BD"    eight LE-u16-ish firmware/config words
```

### With the Jieli element — 31 bytes (two elements)

```
<same 20-byte body> | d6 05 | 08 00 | 4a 4c 41 49 53 44 4b
                      CID     08 =    "JLAISDK"
                      0x05D6  version
                      LE      (jieli_audio's reading)
```

This is **two manufacturer-data elements, not one**: when the
advertising packet and the scan response each carry a `0xFF` structure,
CoreBluetooth concatenates them. The trailing 11 bytes are their own
element under Jieli's CID `0x05D6`, not a CID embedded in the `0x5401`
payload. The same 11 bytes turn up **on their own** in 6 corpus records
(2026-06-12 → 2026-09-29, 4 of them with `0xAF30`, one named), where
`jieli_audio` parses them as an `audio` device and reads `08` as its
version byte (version 8) — see [jieli-audio.md](jieli-audio.md).

The body's `02 00 / 20 00 / 60 05 / 00 00 / 0e 00 / 0a 00 / 67 00 /
00 00` words read as firmware or capability constants; with a single
captured unit there is no evidence any field is per-unit, so **no serial
is decoded and identity stays address-anchored** (the conservative choice
shared with `jieli_ascii_pseudo_cid`).

## Parser scope (passive-only)

NearSight's `jieli_aisdk` parser (2026-10-10 sweep) routes on CID
`0x5401` and AND-requires the `"BD"` body marker plus either the exact
20-byte length or the 31-byte length with the exact
`d6 05 08 00 "JLAISDK"` Jieli element. The 20-byte claim rests on its
byte-for-byte prefix-identity with the 31-byte frame from the same
unit; the exact-element gate keeps an arbitrary 31-byte "BD…" frame
from being claimed. Reports `frame_variant` (`bare` /
`with_jieli_element`), and on the 31-byte frames `jieli_element_hex`,
`jieli_element_version` (jieli_audio's reading: `8`) and
`ascii_label: JLAISDK`. Device class is `audio`, the class `jieli_audio`
gives the same element when it arrives alone.

## Confidence

HIGH on the chipset/SDK attribution (the separate element under Jieli's
real SIG CID `0x05D6`, carrying the "JLAISDK" label, which is also seen
on its own in 6 records) and MEDIUM-LOW on family
coverage (one unit, one day, one uploader — the 20-byte bare claim in
particular rests on one prefix match). No product-line claim is made.
Watch item: a second unit would show whether any body word is per-unit
(thin-serial candidates: none obvious).
