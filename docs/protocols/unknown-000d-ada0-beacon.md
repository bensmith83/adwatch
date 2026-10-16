# Unknown CID 0x000D + svc 0xADA0 beacon family (structured, undecoded payload)

## Overview

An unattributed family of BLE beacons advertising a 25-byte manufacturer
frame under Bluetooth SIG company ID `0x000D` (Texas Instruments) whose
middle 16 bytes change from sighting to sighting — structured but
undecoded content, not ciphertext — while a 3-byte trailing tag stays
fixed per unit across capture days a week apart. Every record co-advertises the unassigned 16-bit
service UUID `0xADA0`, is nameless, and advertises from a random address.

The family dominated the 2026-10-10 NearSight nightly sweep pool (125 of
156 candidate records) and was first analysed on 2026-10-05 (bead
nearsight-65k2), when every unit had been seen exactly once and no stable
field could be proven. The 2026-10-09/10 captures supplied the bead's
requested multi-sighting test: the same two 3-byte tags recur across four
capture days (2026-10-03, 10-04, 10-09, 10-10) while the rest of the
payload changes, so the tag is a per-unit identity anchor that holds
across capture days, not an epoch or frame-type marker.

**No vendor or ecosystem is claimed.** `0x000D` only identifies TI
silicon (TI ships in everything); `0xADA0` is not SIG-assigned and
matches no documented ecosystem; the unit tags are not IEEE OUIs
(`B0:9D:5D`, `D9:77:B5`, `CB:B6:42` all unassigned, either byte order).

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x000D` (wire `0d 00`) | SIG: Texas Instruments — silicon only, no product claim |
| Service UUID | `0xADA0` (advertised) | unassigned; present on every family frame (385/385 25-byte records; 832/832 raw-upload frames, 429/429 in the 2026-10-12 merged export) — **required** by the parser gate |
| Frame | 25 bytes incl. CID, `00 02` at [2..4) | 385 records full-history |
| Unit tag | bytes [22..25) | `b0 9d 5d` (×283), `d9 77 b5` (×101), `cb b6 42` (×1, 2026-07-29; seen again on 2026-10-09, from a different install) |
| Local name | none | 453/453 family records |
| Address | random | rotates; the unit tag does not |
| Device class | `unknown` | |

## Ad Format — 25 bytes

```
offset  0  1 | 2  3 | 4  5 | 6 … 21 | 22 23 24
        0d 00 | 00 02 | slow | undecoded | unit tag
        CID     marker field   body        (identity)
```

| Bytes | Field | Evidence |
|-------|-------|----------|
| 0–1 | CID `0x000D` LE | 385/385 |
| 2–3 | `00 02` marker | 385/385 |
| 4–5 | slow field, LE u16 | per-unit near-constant within a day (~6 values/unit), drifting day-to-day; the two recurring units' values move up/down **together** across capture days (unit A ≈ 8,800–9,830; unit B ≈ 24,900–26,000) — a shared environmental reading of unknown semantics; reported raw, never gated |
| 6–21 | undecoded body | changes per sighting but is **structured, not ciphertext**: across 307 frames of the `b0 9d 5d` unit (2026-10-12 merged export) bytes 11–20 each take only 8, 16 or 32 distinct values and their varying bits repeat a 5-byte pattern; bits 2–6 of byte 7 step like a 5-bit counter; only byte 21 is full-entropy (181 values), and it matches none of the byte sums, XORs or common CRC-8s tried over the bytes before it. The raw uploads (602 distinct frames of that unit) show the same structure, a little looser in bytes 6–10. No decode attempted; reported raw as `undecoded_body_hex` |
| 22–24 | unit tag | stable per unit across 4 capture days a week apart — the identity anchor |

## Parser scope (passive-only)

NearSight's `unknown_000d_ada0` parser (2026-10-10 sweep) claims exactly
the 25-byte `00 02` shape with svc `0xADA0` advertised, reports the tag /
slow field / undecoded body (`undecoded_body_hex`) raw, and keys identity
on the tag (`unknown_000d_ada0:<tag hex>`) because the BLE address
rotates while the tag does not. The service is AND-required: `0x000D` is
TI's silicon ID, shared by every product on a TI chip, and the parser
mints a payload-derived identity, so CID + length + marker alone would be
too thin a gate. Every family record carries it.

### Sibling shapes on CID 0x000D — NOT claimed by any parser

- **24-byte `0d 00 d0 00 …` variant** — 65 records, all on a single day
  (2026-08-23), no co-advertised service, per-record varying tails. A
  different frame type/mode with no proven anchor; documented, unclaimed.
- **ASCII HID frames** (svc `0x1812`): `ERF2p36ADV` (n=10, 2026-07-30),
  `ERF3M90ADV` (n=22, 2026-08-29), and an 18-byte mixed frame embedding
  `ERF3M90` (n=31, same day). Unit-code-like ASCII plus an "ADV"
  (advertising?) suffix. Same rare CID but a different service and
  shape; a shared vendor firmware family is plausible but unproven.
  They are unclaimed: no parser takes them, the unidentified-beacons
  catalogue included.

## Confidence

HIGH on the family fingerprint and the identity anchor (385 records,
cross-day tag recurrence, per-unit slow-field baselines). NONE on
attribution — the honest label is "TI-silicon beacon with a structured,
undecoded payload, svc 0xADA0 ecosystem unidentified". Identifying the 0xADA0 ecosystem is the
remaining win (bead nearsight-65k2 stays open for that half).
