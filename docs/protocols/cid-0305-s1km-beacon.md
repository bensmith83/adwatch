# S1-KM family beacon (reused CID 0x0305 + constant marker)

## Overview

A family of small BLE beacons advertises a 17-byte manufacturer frame
under SIG company ID `0x0305` — a slot registered to **Swipp ApS**, a
defunct Danish mobile-payment app. The slot is reused by an unknown
module vendor, so the family is named by its wire shape and its one
observed local name (`S1-KM_b8c65a`, 2026-07-03), not by the registry.

22 records / 106 sightings across nine capture days (2026-07-03 →
2026-10-01). Every record also advertises the unassigned 16-bit service
UUID `0x1910`. The 2026-08-30 sweep did the analysis (bead 2zqv) and
deferred only to batch the work; the 2026-10-05 nightly sweep re-verified
the map against the full history and shipped the parser
(`CID0305S1KMParser`, `cid_0305_s1km`).

## Supported models

Unknown — `S1-KM` is the only product string ever observed. Key finder,
lock, and e-bike module are all consistent with the shape; none is
claimed.

## BLE advertisement format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0305` (LE `05 03`) | Swipp ApS slot, **reused** — not a vendor claim |
| Manufacturer data | exactly 17 bytes incl. CID | |
| Constant marker | `b0 00 f4 f9 53 65` at [5..11) | the real family anchor |
| Advertised service UUID | `0x1910` | not SIG-assigned; corroboration, not routed |
| Local name | `S1-KM_<unit id prefix>` | seen once (2026-07-03); usually absent |
| Address | random | |

### Byte map (verified against all 22 records)

```
[0..2)   05 03                CID 0x0305 LE
[2]      type                 0x02 (most units) / 0x05 / 0x09 (the named
                              S1-KM unit) — reported raw
[3]      per-unit constant    constant per unit, shared across some units
                              (0x12 ×several) — reported raw
[4]      battery percent      100 on most units; unit 21dcd8d8f68f
                              declined 77 → 75 → 74 across
                              2026-08-18 → 08-22 → 08-29
[5..11)  b0 00 f4 f9 53 65    constant marker on 22/22 records
[11..17) unit id              6 bytes, per unit; the named unit's local
                              name suffix is this field's first 3 bytes
```

Real frames: `0503091064b000f4f95365b8c65abf465b` (the named unit),
`050302124db000f4f9536521dcd8d8f68f` (battery 77).

None of the unit-id prefixes is a registered IEEE OUI (several carry the
locally-administered bit), so the id is a module-scoped value, not a
factory MAC.

### Parser gate

CID `0x0305` + exactly 17 bytes + type byte ∈ {0x02, 0x05, 0x09} +
battery byte ≤ 100 + the constant marker. The marker, not the squatted
CID, is what makes the gate false-positive-safe.

## Identity hashing

```
stableKey      = "cid_0305_s1km:<6-byte unit id hex>"   (payload-derived)
identifierHash = SHA256(stableKey)[:16]
```

The unit id is tagged `.uniqueStable`; the name-suffix match on the one
named unit is the corroboration that the field is the device's own id.

## Parser scope

Passive-only. Reports type, per-unit constant and battery percent raw;
unit id drives identity.

## What we cannot parse

- The vendor and product
- The type byte's semantics (0x09 on the one named unit suggests a
  pairing/idle mode split, unproven)
- Whether the [3] constant is a hardware revision

## Detection significance

A sighting means an S1-KM-family beacon is nearby, re-identifiable across
sessions by its 6-byte id, with a live battery percentage. The reused CID
is itself a fingerprint of cheap-module firmware.

## Confidence / attribution

**Vendor: none claimed** (CID slot reused; the SIG registry name is a
dead company).

**Family coherence: high** — one constant marker, one length, one
service UUID, and a name-suffix corroboration across 22 records over
three months.

**Field semantics: moderate** — the battery reading has a declining
multi-day trend; the unit id has the name-suffix corroboration; the rest
is raw.

## References

- Bead 2zqv (app repo) — the 2026-08-30 analysis this doc formalises.
- Bluetooth SIG company-ID registry — `0x0305 = Swipp ApS` (defunct).
- NearSight `Sources/Parsers/CID0305S1KMParser.swift` and
  `research/sweep-2026-10-05-candidates.md`.
