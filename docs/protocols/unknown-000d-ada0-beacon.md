# Unknown CID 0x000D + svc 0xADA0 rolling-payload beacon family

## Overview

An unattributed family of BLE beacons advertising a 25-byte manufacturer
frame under Bluetooth SIG company ID `0x000D` (Texas Instruments) whose
middle 16 bytes rotate on every sighting — reading as encrypted/rolling
content — while a 3-byte trailing tag stays fixed per unit across capture
days a week apart. Every record co-advertises the unassigned 16-bit
service UUID `0xADA0`, is nameless, and advertises from a random address.

The family dominated the 2026-10-10 NearSight nightly sweep pool (125 of
156 candidate records) and was first analysed on 2026-10-05 (bead
nearside-65k2), when every unit had been seen exactly once and no stable
field could be proven. The 2026-10-09/10 captures supplied the bead's
requested multi-sighting test: the same two 3-byte tags recur across four
capture days (2026-10-03, 10-04, 10-09, 10-10) while every other payload
byte rotates, so the tag is a durable per-unit identity anchor, not an
epoch or frame-type marker.

**No vendor or ecosystem is claimed.** `0x000D` only identifies TI
silicon (TI ships in everything); `0xADA0` is not SIG-assigned and
matches no documented ecosystem; the unit tags are not IEEE OUIs
(`B0:9D:5D`, `D9:77:B5`, `CB:B6:42` all unassigned, either byte order).

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x000D` (wire `0d 00`) | SIG: Texas Instruments — silicon only, no product claim |
| Service UUID | `0xADA0` (advertised) | unassigned; present on 385/385 25-byte records — corroboration, never a gate requirement |
| Frame | 25 bytes incl. CID, `00 02` at [2..4) | 385 records full-history |
| Unit tag | bytes [22..25) | `b0 9d 5d` (×283), `d9 77 b5` (×101), `cb b6 42` (×1, 2026-07-29) |
| Local name | none | 453/453 family records |
| Address | random | rotates; the unit tag does not |
| Device class | `unknown` | |

## Ad Format — 25 bytes

```
offset  0  1 | 2  3 | 4  5 | 6 … 21 | 22 23 24
        0d 00 | 00 02 | slow | rolling | unit tag
        CID     marker field   content   (identity)
```

| Bytes | Field | Evidence |
|-------|-------|----------|
| 0–1 | CID `0x000D` LE | 385/385 |
| 2–3 | `00 02` marker | 385/385 |
| 4–5 | slow field, LE u16 | per-unit near-constant within a day (~6 values/unit), drifting day-to-day; the two recurring units' values move up/down **together** across capture days (unit A ≈ 8,800–9,830; unit B ≈ 24,900–26,000) — a shared environmental reading of unknown semantics; reported raw, never gated |
| 6–21 | rolling content | high entropy per sighting (byte 21 alone: 101 distinct values / 125 records in one pool); no decode attempted |
| 22–24 | unit tag | stable per unit across 4 capture days a week apart — the identity anchor |

## Parser scope (passive-only)

NearSight's `unknown_000d_ada0` parser (2026-10-10 sweep) claims exactly
the 25-byte `00 02` shape, reports the tag / slow field / rolling region
raw, and keys identity on the tag (`unknown_000d_ada0:<tag hex>`) because
the BLE address rotates while the tag does not. Svc `0xADA0` presence is
reported as `ada0_service_advertised` but is not required — uploads can
drop the service list, and the shape gate is already family-specific.

### Sibling shapes on CID 0x000D — NOT claimed

- **24-byte `0d 00 d0 00 …` variant** — 65 records, all on a single day
  (2026-08-23), no co-advertised service, per-record varying tails. A
  different frame type/mode with no proven anchor; documented, unclaimed.
- **ASCII HID frames** (svc `0x1812`): `ERF2p36ADV` (n=10, 2026-07-30),
  `ERF3M90ADV` (n=22, 2026-08-29), and an 18-byte mixed frame embedding
  `ERF3M90` (n=31, same day). Unit-code-like ASCII plus an "ADV"
  (advertising?) suffix. Same rare CID but a different service and
  shape; a shared vendor firmware family is plausible but unproven, so
  these stay with the unidentified-beacons catalogue.

## Confidence

HIGH on the family fingerprint and the identity anchor (385 records,
cross-day tag recurrence, per-unit slow-field baselines). NONE on
attribution — the honest label is "TI-silicon encrypted beacon, svc
0xADA0 ecosystem unidentified". Identifying the 0xADA0 ecosystem is the
remaining win (bead nearsight-65k2 stays open for that half).
