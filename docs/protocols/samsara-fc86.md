# Samsara fleet telematics — 0xFC86 service-data frames

## Overview

**Samsara Networks, Inc.** holds (at least) three Bluetooth SIG *member*
16-bit service UUIDs: `0xFCE5` (see `samsara.md`), `0xFC86` (this doc) and
`0xFC87`. Member UUIDs are allocated only to SIG member companies, so the
allocation itself is the vendor attribution.

On 2026-10-04 a single receiver captured **23 records / 174 sightings** of
a 24-byte service-data frame under `0xFC86` — RSSI −82..−102 dBm, random
addresses, no local name, no manufacturer data. That is the same drive-by
shape as the `0xFCE5` clusters: Samsara-equipped commercial vehicles
passing a fixed receiver. The wire layout is entirely different from the
22-byte `0xFCE5` frames, so this family gets its own parser
(`SamsaraFC86Parser`, `samsara_fc86`) rather than a branch on the sibling.

## Supported models

None pinned. Samsara sells vehicle gateways (VG), asset gateways (AG), AI
dash cams (CM), environmental monitors (EM) and the AT-series asset tags;
nothing in the frame names a product and no Samsara document describes the
advertisement.

## BLE advertisement format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service data | under `0xFC86`, exactly 24 bytes | SIG member UUID → Samsara Networks, Inc. |
| Manufacturer data | none | |
| Local name | none | |
| Address | random | rotates; identity comes from the payload |

### Byte map (verified against all 23 records)

```
[0..3)   81 f0 00          header (constant 23/23)
[3..5)   unit word         20 distinct values over 23 records; units
                           9df8 / eef3 / f6f3 each recur with ONLY [8]
                           or [10] changing — the per-unit field
[5..8)   e4 0f 00          constant 23/23
[8]      8f (21) / 90 (2)  state byte (reported raw)
[9]      29 (22) / 31 (1)  state byte (reported raw)
[10]     ff (9) / fe (9) / fd (5)  low-cardinality state/counter (raw)
[11..14) 17 80 0d          constant 23/23
[14..24) 00 ×10            constant padding 23/23
```

Real frame: `81f0009df8e40f008f29ff17800d00000000000000000000`.

The two bytes at [3..5) cluster in two bands (0xF39x–0xF4xx and
0xF7xx–0xF8xx as a little-endian word); whether that split is a product
or fleet distinction is unknown.

### Parser gate

`0xFC86` service data of exactly 24 bytes, header `81 f0 00`, constants
`e4 0f 00` at [5..8), `17 80 0d` at [11..14), and an all-zero pad at
[14..24). Everything else is surfaced raw.

## Identity hashing

```
stableKey      = "samsara_fc86:<unit word hex>"   (payload-derived)
identifierHash = SHA256(stableKey)[:16]
```

The unit word recurred unchanged on all three units captured twice, so it
is the identity anchor (tagged `.uniqueStable`). **Caveat:** every capture
is from a single day (2026-10-04), so the word is verified stable only
within that window — the same posture `qualcomm_esl_tag` records for its
tag id. If a future capture shows the word re-minting daily, the key
degrades to per-day identity.

## Parser scope

Passive-only (`samsara_fc86`, NearSight 2026-10-05 nightly sweep). No
connect, no service reads; semantics of bytes [3..14) are not decoded.

## What we cannot parse

- Which Samsara product emits these frames
- The meaning of the unit word's two bands, and of the three state bytes
- Any telemetry (no field varies like a sensor reading; the fleet was
  drive-by, so nothing trended)

## Detection significance

A sighting means a Samsara-connected fleet asset is within BLE range — a
truck cab, delivery van, or tagged equipment — same as the `0xFCE5`
family. Within a capture window the unit word re-identifies the unit.

## Confidence / attribution

**Vendor: high.** A SIG member UUID registered to Samsara on every record;
the frame shape is regular across 23 independent units.

**Product: low / not claimed.**

**Field semantics: low.** Only the constancy structure is asserted; all
non-constant fields are reported raw.

## References

- Bluetooth SIG `member_uuids.yaml` — `0xFC86 = Samsara Networks, Inc`.
- `samsara.md` (this repo) — the `0xFCE5` sibling family and Samsara
  product-line background.
- NearSight `Sources/Parsers/SamsaraFC86Parser.swift` and
  `research/sweep-2026-10-05-candidates.md` (app repo) — the sweep that
  shipped the parser.
