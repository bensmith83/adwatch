# Jieli "JLAISDK" self-labelled beacon (pseudo-CID 0x5401)

## Overview

A device on **Zhuhai Jieli** silicon/firmware that broadcasts the AI-SDK
toolchain's own label instead of a SIG company ID — the same self-label
genre as the "ZHJIELI" frame ([jieli-audio.md](jieli-audio.md) covers
Jieli's real SIG slot `0x05D6`; the ZHJIELI ASCII pseudo-CID `0x485A`
spells "ZH").

One unit captured on 2026-10-09 (2 records / 7 sightings, one uploader),
nameless, co-advertising the unassigned 16-bit service UUID `0xAF30`,
emitting two frame variants — a 20-byte body, and the same body with an
11-byte self-label tail appended.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | pseudo-CID `0x5401` (wire `01 54`) | unassigned; frame bytes 1–3 spell ASCII "TBD" across the CID/payload boundary |
| Service UUID | `0xAF30` (advertised) | unassigned; 2/2 records — corroboration, not a gate |
| Embedded CID | tail opens `d6 05` = **`0x05D6` LE — Jieli's real SIG CID** | the primary attribution |
| ASCII label | tail bytes 24–30 = `"JLAISDK"` (JL AI SDK) | the secondary attribution |
| Local name | none | |
| Device class | `peripheral` | |

## Ad Format

### Bare variant — 20 bytes

```
01 54 | 42 44 | 02 00 20 00 60 05 00 00 0e 00 0a 00 67 00 00 00
CID     "BD"    eight LE-u16-ish firmware/config words
```

### Labelled variant — 31 bytes

```
<same 20-byte body> | d6 05 | 08 00 | 4a 4c 41 49 53 44 4b
                      CID       len?    "JLAISDK"
                      0x05D6 LE
```

The body's `02 00 / 20 00 / 60 05 / 00 00 / 0e 00 / 0a 00 / 67 00 /
00 00` words read as firmware or capability constants; with a single
captured unit there is no evidence any field is per-unit, so **no serial
is decoded and identity stays address-anchored** (the conservative choice
shared with `jieli_ascii_pseudo_cid`).

## Parser scope (passive-only)

NearSight's `jieli_aisdk` parser (2026-10-10 sweep) routes on CID
`0x5401` and AND-requires the `"BD"` body marker plus either the exact
20-byte length or the 31-byte length with the exact
`d6 05 08 00 "JLAISDK"` tail. The 20-byte claim rests on its
byte-for-byte prefix-identity with the self-labelled frame from the same
unit; the tail gate keeps an arbitrary 31-byte "BD…" frame from being
claimed. Reports `frame_variant` (`bare` / `labelled`), and on labelled
frames `ascii_label: JLAISDK` + `embedded_company_id: 0x05D6`.

## Confidence

HIGH on the chipset/SDK attribution (two independent self-labels: the
embedded real SIG CID and the ASCII tag) and MEDIUM-LOW on family
coverage (one unit, one day, one uploader — the 20-byte bare claim in
particular rests on one prefix match). No product-line claim is made.
Watch item: a second unit would show whether any body word is per-unit
(thin-serial candidates: none obvious).
