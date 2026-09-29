# RAB Lighting BLE Mesh Fixture Beacon (CID 0x07A5)

## Overview

**RAB Lighting, Inc.** is a US commercial/industrial lighting manufacturer
whose **Lightcloud Blue** line is a Bluetooth-mesh lighting-control system
(luminaires, wall controllers, sensors) managed from a phone app — no
gateway required. Company identifier `0x07A5` is SIG-registered to RAB
Lighting, Inc.

The capture behind this doc is a **29-device single-site fleet** seen in one
evening (2026-09-25, full-history corpus: 50 records / 435 sightings),
which is exactly the shape of a commercial Lightcloud Blue install: dozens
of co-located fixtures, all advertising continuously. Two advertisement
surfaces appear on the same units:

| Surface | Content | Claimed by |
|---|---|---|
| Service data `0x1828` | Bluetooth Mesh **proxy** PDU: `00` + 8-byte network ID | `bt_mesh` (generic Bluetooth Mesh parser) |
| Manufacturer data CID `0x07A5` | RAB vendor config frame (this doc) | `rab_lighting` |

The mesh-proxy surface confirms these units are Bluetooth Mesh nodes; the
vendor frame below is the RAB-specific half.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Company ID | `0x07A5` (LE wire bytes `a5 07`) — RAB Lighting, Inc. |
| Manufacturer-data total length | 29 bytes (2-byte CID + 27-byte payload) |
| Payload marker (offsets 3-5) | `11 1f 78` |
| Payload constants | offset 6 = `01`, offset 8 = `10` |
| Local name | absent in all captures |
| Address type | random |

Match rule (false-positive-safe): CID `0x07A5` **and** 27-byte payload
**and** the `11 1f 78` marker **and** both `01`/`10` constants. CID-only
frames or marker-broken frames are left unclaimed.

### Byte Map (payload offsets, after the 2-byte LE CID)

```
 0-2    per-unit id (3 bytes; constant per unit, distinct per unit)
 3-5    marker `11 1f 78`              (30/30 frames)
 6      `01`                           (30/30 frames)
 7      device-type code               (see table)
 8      `10`                           (30/30 frames)
 9      status byte                    (0x40 most common)
10-11   config word                    (correlates with type code)
12-13   value word                     (0xffff = unset on most types)
14-26   zeros
```

Every unit re-emits **one byte-identical frame** across all sightings, so
this is a provisioning/config beacon, not live telemetry.

### Observed Type Codes (29-device capture)

| Type code | Frames | Config word | Value word | Notes |
|---|---|---|---|---|
| `0x55` | 17 | `08 00` / `09 00` | `ff ff` (unset) | most common family at the site |
| `0x48` | 9 | `0a 01` / `0a 00` / `0a 03` | `3c 05` / `29 00` | the only family carrying a set value |
| `0x4a` | 1 | `08 00` | `ff ff` | |
| `0x24` | 1 | `08 00` | `00 00` | |

The type/config correlation supports a product-family split (two fixture
families at the site). No public byte-format documentation exists, so the
parser surfaces `device_id`, `device_type_code`, `status_byte`,
`config_hex`, `value_hex` **raw** and claims no semantics beyond the split.

### Parser Scope (Passive Only)

Presence + vendor attribution + raw config fingerprint. No control, no
mesh-key material, no decoding of the (encrypted) mesh PDUs on the `0x1828`
surface.

### Identity

The advertised address is a random static/private address and the capture
is a single day, so cross-day stability of the 3-byte on-air id is
unproven: the parser keys identity on the MAC and sets **no stable key**.
The 3-byte id is emitted in metadata as a re-identification candidate
pending a second-day capture.

## Confidence / Attribution

- **Attribution: HIGH.** SIG-registered CID + Bluetooth Mesh proxy service
  data on sibling records from the same units + a 29-device commercial
  fleet matching RAB's Lightcloud Blue deployment model.
- **Byte semantics: MEDIUM.** The type/config split is correlational
  (single site, single day). Status/config/value fields are surfaced raw
  with no unit claims.

## References

- Bluetooth SIG company identifiers — `0x07A5` = RAB Lighting, Inc.
- NearSight app repo: `Sources/Parsers/RabLightingParser.swift`,
  `research/sweep-2026-09-29-candidates.md`
- RAB Lightcloud Blue product line (Bluetooth mesh lighting controls):
  rablighting.com
