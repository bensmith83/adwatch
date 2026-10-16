# Samsara fleet telematics — 0xFC86 service-data frames

## Overview

**Samsara Networks, Inc.** holds five Bluetooth SIG *member* 16-bit
service UUIDs: `0xFE9B`, `0xFCE4`, `0xFCE5` (see `samsara.md`), `0xFC86`
(this doc) and `0xFC87`. Member UUIDs are allocated only to SIG member
companies, so the allocation itself is the vendor attribution.

On 2026-10-04 a single receiver captured **23 records / 174 sightings**
(first sightings 11:11–11:35Z) of a 24-byte service-data frame under
`0xFC86` — RSSI −82..−102 dBm, random addresses, no local name, no
manufacturer data. That is the same drive-by
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
| Address | random | identity is the BLE address (see Identity hashing) |

### Byte map (verified against all 23 records)

```
[0..3)   81 f0 00          header (constant 23/23)
[3..5)   unit word         20 distinct values over 23 records;
                           9df8 / eef3 / f6f3 each recur with ONLY [8]
                           or [10] changing, each time from the SAME
                           BLE address — a per-unit field or a reading
[5..8)   e4 0f 00          constant 23/23
[8]      8f (21) / 90 (2)  state byte (reported raw)
[9]      29 (22) / 31 (1)  state byte (reported raw)
[10]     ff (9) / fe (9) / fd (5)  low-cardinality state/counter (raw)
[11..14) 17 80 0d          constant 23/23
[14..24) 00 ×10            constant padding 23/23
```

Real frame: `81f0009df8e40f008f29ff17800d00000000000000000000`.

The two bytes at [3..5) cluster in two bands (0xF39x–0xF4xx and
0xF7xx–0xF8xx as a little-endian word): the high byte is `f3`, `f7` or
`f8` (one `f4`). That fits a signed sensor reading as well as an id;
whether the split is a reading, a product or a fleet distinction is
unknown.

A 7-byte frame under `0xFC86` was also seen on 2026-10-03; it does not
fit this layout and is left unclaimed.

### Parser gate

`0xFC86` service data of exactly 24 bytes, header `81 f0 00`, constants
`e4 0f 00` at [5..8), `17 80 0d` at [11..14), and an all-zero pad at
[14..24). Everything else is surfaced raw.

## Identity hashing

```
stableKey      = nil
identifierHash = SHA256(ble_address)[:16]   (address-anchored)
```

Identity is the BLE address, not the payload. Every record comes from
one uploading phone in one window on 2026-10-04, and each of the three
unit words that repeated did so from the same address, so the address
already links those sightings and nothing shows the word is a unit id
rather than a reading. The word is still reported (`unit_word_hex`,
tagged `.uniqueStable` in case it is an id). Revisit if a later capture
day shows a word surviving an address change; that is what would justify
a payload key.

## Parser scope

Passive-only (`samsara_fc86`, NearSight 2026-10-05 nightly sweep). No
connect, no service reads; semantics of bytes [3..14) are not decoded.

## What we cannot parse

- Which Samsara product emits these frames
- Whether the unit word is an id or a reading, the meaning of its two
  bands, and of the three state bytes
- Any telemetry (nothing is decoded as one; the fleet was drive-by, so
  nothing trended)

## Detection significance

A sighting means a Samsara-connected fleet asset is within BLE range — a
truck cab, delivery van, or tagged equipment — same as the `0xFCE5`
family. Repeat sightings are linked by the BLE address only.

## Confidence / attribution

**Vendor: high.** A SIG member UUID registered to Samsara on every record;
the frame shape is regular across all 23 records.

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
