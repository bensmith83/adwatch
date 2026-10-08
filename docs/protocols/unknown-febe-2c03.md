# Unknown BLE Family — CID `0x2C03` + FEBE Service UUID

## Overview

A BLE family that co-advertises the unassigned Bluetooth SIG company ID
**`0x2C03`** (on-wire bytes `03 2c`) alongside the SIG-member service UUID
**`0xFEBE`**. `0xFEBE` is **Bose Corporation's** SIG-registered service
UUID — the same UUID that routes real Bose earbuds through
`BoseFEBEEarbudsParser` — and the frame shape matches the Bose+Telink
`03 NN` family that parser already claims (see below). But no `0x2C03`
unit has ever broadcast a local name, and the Bose-attribution decision
for the wider `03 NN` / `01 NN` FEBE frame space is an explicitly
pending operator call, so the family is catalogued here as
`vendor: Unknown` with a fingerprint-only parser (`unknown_febe_2c03`).

Unlike the three withheld sibling families — `unknown_febe_0601` (Bose
vs. Schrader Electronics), `unknown_febe_0a01` (Bose vs. Cleveron AS),
`unknown_febe_0b01` (Bose vs. Resideo Technologies) — CID `0x2C03` has
**no SIG registry entry at all** (current max assigned ≈ `0x10C7`), so
there is no second named vendor: Bose is the lone candidate, withheld
rather than denied.

This parser is deliberately named `unknown_febe_2c03`, **not**
`unknown_febe`: the bare FEBE service UUID alone already routes to real
Bose devices via `BoseFEBEEarbudsParser`, so this parser is scoped to
the **`0x2C03` + FEBE** combination specifically and must not shadow
that broader FEBE family.

## Fingerprint

### Service UUID

| UUID | Notes |
|------|-------|
| `0xFEBE` | SIG-member service UUID, registered to Bose Corporation. Required alongside the CID for this parser to claim. |

### Company ID

| CID (LE-decoded) | On-wire bytes | SIG assignment |
|------------------|---------------|----------------|
| `0x2C03` | `03 2c` | **Unassigned** (above the current registry max ≈ `0x10C7`) — vanity/unregistered value |

### Manufacturer Data

Two physical units observed (full-corpus history, 2026-08-26 and
2026-09-29 — a month apart), both nameless, addressType random, 13-byte
manufacturer data with an identical 4-byte head:

```
unit A (2026-09-29, 3 sightings):  03 2c | 51 12 | xx xx xx xx xx xx xx xx xx
unit B (2026-08-26, 5 sightings):  03 2c | 51 12 | yy yy yy yy yy yy yy yy yy
                                    CID    type     per-unit rolling hash
```

- **Bytes 0–1**: `03 2c` on wire → LE-decoded CID `0x2C03` (unassigned).
- **Bytes 2–3**: constant `51 12` type prefix across both units. The
  same `51 1x` prefix appears in the labelled byte-0 0x01 FEBE family
  (`01 09 51 12 …` → "LE-Bose QC35 II") and in the Bose-claimed
  `03 47` / `03 37` frames (`51 10`, `52 10`, `41 08`, …) — strong
  structural evidence that all of these are one frame family whose
  first two bytes are a frame tag + product/subtype code rather than a
  company ID at all. Semantics unknown; surfaced as `type_prefix`.
- **Bytes 4–12**: a 9-byte per-unit value, distinct per unit and stable
  within a capture window. Same rolling-hash convention as the Bose
  `0x4703`/`0x3703` frames (documented in `bose-febe.md` as rolling, not
  a durable serial) — surfaced raw in `payload_hex`, **not** used as a
  stable key.

### Local Names

None ever captured on a `0x2C03` frame. This is the decisive gap: the
Bose-claimed `03 NN` CIDs (`0x4703`, `0x3703`) both arrived with
Bose-substring names ("LE-Bose QC Headphones", "LE-<owner> Bose",
"LE-Bose QC45"); this family has none.

## Identification

- **Primary**: CID `0x2C03` **and** service UUID `0xFEBE` co-advertised.
  The parser guards on both; neither alone triggers a claim (FEBE alone
  belongs to the broader Bose family).
- **Secondary** (informational): the constant `51 12` type prefix
  confirms the frame is in its expected shape.
- **Device class**: `unknown` — the parser is fingerprint-only and makes
  no vendor or product claim.

## Relationship to the Bose `03 NN` / `01 NN` Frame Space

This family sits inside a contested attribution space:

- `bose_febe` claims `0x4703` (Telink big-endian CID quirk) and `0x3703`
  (vanity-unregistered) **with** name evidence.
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
  above a misread — including this one. `unknown_febe_2c03` is the
  conservative holding pattern: identity and clustering now, attribution
  later.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Family flag | CID `0x2C03` + service UUID `0xFEBE` | "We've seen this family before" |
| `type_prefix` | mfr bytes 2–3 | constant `0x5112` across both units |
| `payload_hex` | mfr bytes 2–12 | type prefix + 9-byte rolling hash, raw |
| `attribution_note` | derived | records the Bose candidate and why attribution is withheld |

## What We Cannot Parse

- Vendor / brand / product class — attribution is deliberately withheld;
  no labelled specimen yet.
- Semantics of the type prefix and the 9-byte tail (rolling pairing
  token? truncated hash?).
- Whether the device is audio hardware (implied by FEBE/Bose) or
  something else riding the same ODM firmware.

## Stable Identity

The 9-byte tail rolls within a capture window (same convention as the
Bose `0x4703`/`0x3703` frames), so it is not a durable serial. Identity
anchors on the BLE MAC — `stable_key = unknown_febe_2c03:<mac>` — so
distinct physical units don't collapse into one card. Re-grouping across
MAC rotations will need richer payload sampling in the future.

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
    family (including the `0x4703` Telink-BE and `0x3703` vanity paths)
    this parser deliberately does **not** join.
  - `unknown-febe-0b01.md` / `UnknownFEBE0B01Parser` — the sibling
    withheld-attribution family whose shape this parser mirrors.
