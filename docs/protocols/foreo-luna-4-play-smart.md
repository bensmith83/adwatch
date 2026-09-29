# FOREO LUNA 4 Play Smart (CID 0xFFFF placeholder frame + 0xFFF0)

## Overview

**FOREO AB** (Sweden) makes the LUNA line of sonic facial-cleansing
brushes; the **LUNA 4 Play Smart** (FCC ID `2AT72-LUNA4PLAY`) adds skin
sensors and a Bluetooth link to the "FOREO For You" app. It advertises the
local name `LUNA4PlaySmart` in a scan response and a 12-byte manufacturer
frame under the SIG "no company assigned" placeholder CID `0xFFFF`, with
the generic 16-bit service UUID `0xFFF0` beside it.

Two units are in the NearSight corpus:

| First seen (UTC) | Records | Frame (manufacturer data) | Name captured? |
|------------------|---------|---------------------------|----------------|
| 2026-06-09 21:34 | 2 (7 sightings) | `ffff ffff 0081f9245b82 ff01` | yes on one record, **no** on the other — same identifier, same frame |
| 2026-08-30 17:20–17:25 | 2 (30 sightings) | `ffff ffff e07dea99b975 ff01` | no |

The uploading device's coarse classifier had tagged the 08-30 unit
"inkbird" on the strength of `0xFFF0` alone, which is what put it in the
2026-09-02 sweep's unparsed pool.

## Supported models

| Model | Local name | Frame |
|-------|-----------|-------|
| LUNA 4 Play Smart | `LUNA4PlaySmart` | `ff ff` · `ff ff` · TI-OUI MAC · `ff 01` |

Other FOREO products (LUNA 4, LUNA 4 Plus, BEAR, UFO) have not been
captured and are not claimed.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0xFFFF` (LE wire `ff ff`) | SIG reserved placeholder — never keyed on alone |
| Service UUID | `0xFFF0` | Generic vendor slot shared with Inkbird, SP110E and many others — corroboration only |
| Embedded MAC | 6 bytes at payload [2..8), **forward** order | `00:81:f9:24:5b:82`, `e0:7d:ea:99:b9:75` — both in Texas Instruments MA-L blocks (the CC26xx-class BLE SoC) |
| Local name | `LUNA4PlaySmart`, exact | Carried in a scan response; absent on 2 of the 4 records |
| Address type | random | The 06-09 unit's address stayed put within the session |
| Device class | `personal_care` | |

## Ad Format — manufacturer data, 12 bytes

```
offset  0  1 | 2  3 | 4  5  6  7  8  9  | 10 11
        ff ff | ff ff | e0 7d ea 99 b9 75 | ff 01
        CID     pad     factory MAC          trailer
```

| Bytes | Meaning | Evidence |
|-------|---------|----------|
| 0–1 | CID `0xFFFF` | 4/4 records |
| 2–3 | pad `ff ff` | 4/4 records |
| 4–9 | factory MAC, forward byte order | OUI resolves to Texas Instruments on both units (two different TI blocks) |
| 10–11 | trailer `ff 01` | 4/4 records; semantics unknown |

### Parser gate

- Named path (v1.0): local name exactly `LUNA4PlaySmart`.
- Nameless path (v1.1, 2026-09-02 sweep): **no** local name, CID `0xFFFF`,
  exactly 10 payload bytes, `ff ff` at [0..2), `ff 01` at [8..10), `0xFFF0`
  in the advertised UUID list, **and** a Texas Instruments OUI on the
  embedded MAC.

Any other local name is declined even when the frame matches. The frame's
bookends and `0xFFF0` are too generic to claim a FOREO product without the
TI-OUI corroboration; a second vendor's device with this exact shape and a
TI radio would be a false claim, which is why the gate is this tight and
why the named capture from the same unit (06-09) is the evidence for it.

## Identity Hashing

```
frame present:   identifier = SHA256("foreo_luna4_play_smart:{embedded_mac}")[:16]
                 stableKey  = same                   (embedded_mac tagged uniqueStable)
name only:       identifier = SHA256("foreo_luna4_play_smart:{ble_address}")[:16]
```

The embedded factory MAC anchors identity on both paths, so the 06-09 unit
resolves to one device whether or not its name was captured.

## What We Cannot Parse

- Battery, mode, cleansing session state — nothing in the frame varies
- The trailer bytes
- Skin-sensor data (app-side over GATT)

## Detection Significance

A sighting means a FOREO LUNA 4 Play Smart is powered on within BLE range —
a bathroom counter. The brush broadcasts its factory MAC in the clear, so it
is re-identifiable across sessions regardless of address rotation.

## Confidence / Attribution

**Vendor / product: high on the named capture** (the product's own
advertised name plus FOREO's FCC filing); **medium-high on the nameless
frame** — identical 12-byte shape to the named unit, from a unit that also
emitted the frame nameless, with a TI radio on both.

**Field semantics: low** beyond the embedded MAC.

## References

- FCC ID `2AT72-LUNA4PLAY` (FOREO AB), LUNA 4 play family.
- IEEE MA-L registry — `00:81:F9`, `E0:7D:EA` = Texas Instruments.
- NearSight `FOREOLuna4PlaySmartParser` (v1.1) and
  `research/sweep-2026-09-02-candidates.md`.
