# HP Inc. FDF7 Printer / Accessory Beacon

## Overview

`0xFDF7` is a 16-bit service UUID allocated by the Bluetooth SIG to **HP
Inc.** HP printers, scanners, and accessories broadcast this beacon in
pairing-discoverable mode for HP Smart Tasks proximity pairing. The
advertisement carries a rotating resolvable token (HP's protection
against passive long-term tracking) and a fixed protocol-version trailer.

The advertisement is identification + presence only — live state (ink
level, job queue, paper status) lives behind the HP Smart cloud /
network printing surface.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service-data UUID | `FDF7` | HP Inc. (BT SIG) |
| Manufacturer data | (none) | |
| Local name | (none) | |

The parser matches on the `FDF7` service-data key alone.

## Wire Format

```
01 [16-byte resolvable token] 00 00 00 00 03
└┬┘                            └──┬─────────┘
 frame type (constant)            protocol-version trailer (constant)
```

| Offset | Bytes | Field |
|--------|-------|-------|
| 0      | 1     | `frame_type` — `0x01` across all captures |
| 1–16   | 16    | `resolvable_token` — opaque, rotates between sightings of the same unit |
| 17–20  | 4     | constant `00 00 00 00` |
| 21     | 1     | `protocol_version` — `0x03` across all captures |

Frame length is exactly 22 bytes; anything else is rejected. The leading
`0x01` and trailing `00 00 00 00 03` are stable across all 13 distinct
units captured in `adwatch_export 14`.

## Captured Examples

```
serviceData[FDF7] = 01 f3 33 0e 2b aa 05 53 5a 83 3c 22 44 af 7a ad 02
                       00 00 00 00 03
serviceData[FDF7] = 01 ca 8f 6b 0a fc d8 40 54 94 1c 59 ae 63 24 20 2a
                       00 00 00 00 03
serviceData[FDF7] = 01 d3 08 8a ed a1 38 47 c7 af 46 a9 85 b4 9c 0e b0
                       00 00 00 00 03
serviceData[FDF7] = 01 89 95 58 5d 2a c3 4f 67 8e 46 d4 4a 6c 15 b8 a0
                       00 00 00 00 03
```

Captured 2026-05-23 → 2026-05-29 in `research/adwatch_export 14.json` —
13 distinct devices, 69 sightings total.

## Identity Hashing

```
identifier_hash = SHA256("hp_fdf7:mac:<MAC>")[:16]
```

The 16-byte `resolvable_token` rotates between sightings, so it cannot
anchor a per-unit identity. We fall back to the current BD_ADDR; the HP
Smart pairing protocol requires GATT to derive a stable identifier from
the resolvable token (an HP-private key holder is required).

## Why FDF7 Without a Logical Vendor Match

A subset of records with `FDF7` service-data are also parsed by the
existing `BoseParser` — because Bose advertisements separately carry the
Bose CID `0x009E` in those captures and the registry dispatches both
parsers. `FDF7`-only frames (no CID, no localName) are HP, not Bose.

## What We Cannot Parse Without GATT / HP Smart Cloud

- Specific printer model (HP Smart Tank, OfficeJet Pro, LaserJet, etc.)
- Ink / toner levels
- Job queue / current status
- Firmware version
- Pairing state / paired-host identity

## References

- BT SIG member_uuids.yaml: `0xFDF7 → HP Inc.`
- [HP Smart pairing protocol overview (developer doc)](https://developers.hp.com/hp-print/doc/hp-smart-pairing-protocol)
- Local export 14 capture — 13 distinct units confirm the wire format is
  consistent across the HP product line.
