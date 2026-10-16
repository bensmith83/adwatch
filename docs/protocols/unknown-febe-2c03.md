# BLE Family — CID `0x2C03` + FEBE Service UUID (Bose, folded into `bose_febe`)

> **Status (2026-10-16): attributed to Bose.** NearSight's `bose_febe`
> v1.1 claims CID `0x2C03` + FEBE, named or not
> (`wire_format = bose_febe_vanity_2c03`); the current decode is in
> [bose-febe.md](bose-febe.md). The fingerprint-only `unknown_febe_2c03`
> parser this page first described never landed. The analysis below is
> kept, with its withheld-attribution reading corrected.

## Overview

A BLE family that co-advertises the unassigned Bluetooth SIG company ID
**`0x2C03`** (on-wire bytes `03 2c`) alongside the SIG-member service UUID
**`0xFEBE`**. `0xFEBE` is **Bose Corporation's** SIG-registered service
UUID — the same UUID that routes real Bose earbuds through
`BoseFEBEEarbudsParser` — and the frame shape matches the Bose+Telink
`03 NN` family that parser already claims (see below). This page first
catalogued the family as `vendor: Unknown`, on the belief that no
`0x2C03` unit had ever broadcast a local name. That was wrong: in a raw
2026-09-30 upload, one unit has two records with the same manufacturer
data and FEBE, one unparsed and one claimed by `bose_febe`'s name-keyed
vanity path, which for this CID fires only when the local name contains
"Bose". The claimed record shows no name because `bose_febe` is not a
name-gated parser (its names never upload), and no `product` key
because the upload's stable-key pre-image scrub removed it (that path
keys on the name). That is the same evidence class that put `0x3703`
into `bose_febe`, and the operator call (2026-10-16) attributed the
family to Bose.

Unlike the three withheld sibling families — `unknown_febe_0601` (Bose
vs. Schrader Electronics), `unknown_febe_0a01` (Bose vs. Cleveron AS),
`unknown_febe_0b01` (Bose vs. Resideo Technologies) — CID `0x2C03` has
**no SIG registry entry at all** (current max assigned ≈ `0x10C7`), so
there is no second named vendor: Bose was the lone candidate, and is
now the attribution.

`bose_febe` claims the **`0x2C03` + FEBE** combination on its own path:
FEBE required, name optional. It does not go through the name-keyed
vanity path, whose identity is the name, where every nameless unit
would share one key.

## Fingerprint

### Service UUID

| UUID | Notes |
|------|-------|
| `0xFEBE` | SIG-member service UUID, registered to Bose Corporation. Required alongside the CID for `bose_febe`'s `0x2C03` path to claim. |

### Company ID

| CID (LE-decoded) | On-wire bytes | SIG assignment |
|------------------|---------------|----------------|
| `0x2C03` | `03 2c` | **Unassigned** (above the current registry max ≈ `0x10C7`) — vanity/unregistered value |

### Manufacturer Data

Three physical units observed in the raw corpus (2026-08-26,
2026-09-29 and 2026-10-03), every one with FEBE in its raw upload,
addressType random, 13-byte manufacturer data with an identical 4-byte
head:

```
unit A (2026-09-29, 3 sightings):  03 2c | 51 12 | xx xx xx xx xx xx xx xx xx
unit B (2026-08-26, 5 sightings):  03 2c | 51 12 | yy yy yy yy yy yy yy yy yy
unit C (2026-10-03):               03 2c | 51 12 | zz zz zz zz zz zz zz zz zz
                                    CID    type     per-unit rolling hash
```

- **Bytes 0–1**: `03 2c` on wire → LE-decoded CID `0x2C03` (unassigned).
- **Bytes 2–3**: constant `51 12` type prefix across all three units. The
  same `51 1x` prefix appears in the labelled byte-0 0x01 FEBE family
  (`01 09 51 12 …` → "LE-Bose QC35 II") and in the Bose-claimed
  `03 47` / `03 37` frames (`51 10`, `52 10`, `41 08`, …) — strong
  structural evidence that all of these are one frame family whose
  first two bytes are a frame tag + product/subtype code rather than a
  company ID at all. Semantics unknown; surfaced as `type_prefix`.
- **Bytes 4–12**: a 9-byte per-unit value, distinct per unit and stable
  within a capture window. Same rolling-hash convention as the Bose
  `0x4703`/`0x3703` frames (documented in `bose-febe.md` as rolling, not
  a durable serial) — surfaced raw as `bose_device_hash_hex`; `bose_febe`
  uses the full manufacturer data only as a same-burst key (see Stable
  Identity).

### Local Names

No name appears on any `0x2C03` record in the corpus, but that is an
upload artifact, not evidence of nameless units: `bose_febe`'s names
never upload. The 2026-09-30 record of unit A that `bose_febe`'s vanity
path claimed shows the unit broadcast a "Bose" name. The Bose-claimed
`03 NN` CIDs (`0x4703`, `0x3703`) arrived with Bose-substring names
("LE-Bose QC Headphones", "LE-<owner> Bose", "LE-Bose QC45"); `0x2C03`
joins them on the same class of evidence.

## Identification

- **Primary**: CID `0x2C03` **and** service UUID `0xFEBE` co-advertised.
  `bose_febe` guards on both; neither alone triggers this path (FEBE
  alone belongs to the broader Bose family). A name is optional.
- **Secondary** (informational): the constant `51 12` type prefix
  confirms the frame is in its expected shape.
- **Device class**: `audio`, as for every `bose_febe` claim; no product
  is pinned.

## Relationship to the Bose `03 NN` / `01 NN` Frame Space

This family sits inside a contested attribution space:

- `bose_febe` claims `0x4703` (Telink big-endian CID quirk), `0x3703`
  (vanity-unregistered) and, since v1.1, `0x2C03` — each **with** name
  evidence.
- `unknown_febe_0601` / `0a01` / `0b01` withhold attribution on the
  byte-0 0x01 branch (SIG-assigned CIDs pointing at non-Bose vendors).
- The byte-0 0x03 branch's unclaimed remainder — `0x1C03` (9 records /
  31 sightings in full history), `0x3803` (7 / 15), `0x1D03` (2 / 7),
  `0x2403` (2 / 2) — stays unclaimed tonight; all their signatures are
  already in the analyzed ledger from earlier sweeps.
- Whether the whole space folds into `bose_febe` is the subject of an
  open operator-owned decision (NearSight bead `adwatch-app-vr66`, P1):
  its structural argument is that byte 0 (`0x01`/`0x03`) is a frame
  group tag and byte 1 a product code, which would make every "CID"
  above a misread — including this one. The 2026-10-16 ruling settled
  `0x2C03` only; the sibling `03 NN` CIDs above stay unclaimed.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| `wire_format` | CID `0x2C03` + service UUID `0xFEBE` | `bose_febe_vanity_2c03` |
| `type_prefix` | mfr bytes 2–3 | constant `0x5112` across all three units |
| `bose_device_hash_hex` | mfr bytes 4–12 | 9-byte rolling hash, raw |
| `payload_hex` | mfr bytes 2–12 | type prefix + 9-byte rolling hash, raw |

## What We Cannot Parse

- Which Bose product it is — no name in the corpus pins a model.
- Semantics of the type prefix and the 9-byte tail (rolling pairing
  token? truncated hash?).

## Stable Identity

The 9-byte tail rolls within a capture window (same convention as the
Bose `0x4703`/`0x3703` frames), so it is not a durable serial.
`bose_febe` keys identity on the full manufacturer-data hex, not the
MAC — `stableKey = bose_febe_2c03:<mfg hex>`, like `0x3703` — but keeps
the name out of the identifier hash (the `0x3703` path mixes it in), so
a unit's named and nameless frames from the same moment agree.

## Parser Scope

Passive observation only. No GATT connection, no active probing.

## References

- Bluetooth SIG company identifiers (YAML mirror) — confirms `0x2C03`
  has no assignment (absent from the registry):
  <https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml>
- Bluetooth SIG member UUIDs (YAML mirror) — confirms
  `0xFEBE = Bose Corporation`:
  <https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml>
- Companion / sibling docs and parsers:
  - `bose-febe.md` / `BoseFEBEEarbudsParser` — the FEBE-attributed Bose
    family (including the `0x4703` Telink-BE and `0x3703` vanity paths),
    which claims this family since v1.1.
  - `unknown-febe-0b01.md` / `UnknownFEBE0B01Parser` — the sibling
    withheld-attribution family whose shape the draft parser mirrored.
