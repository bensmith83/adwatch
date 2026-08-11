# Unknown Derived-UUID Cluster (UUIDv4 / v5 / v6 forensic detector)

## Overview

A forensic-cluster parser, parallel to `Static00E0BeaconParser` and
`VendorNode2A2AE2DBCCE4Parser`, that matches unattributed devices
advertising a **single 128-bit service UUID and nothing else** — no
manufacturer data, no service data, no local name. The defining
forensic signal is the UUID itself: when an algorithmic generator
(SHA-1 namespace hash, Gregorian-time, or even random v4) is used to
mint a service UUID, the version nibble alone is a useful lead, and
the UUID literal is a deterministic per-device cluster anchor.

Optional anecdotal `vendor_lead` metadata surfaces when a public
sighting on a different platform has narrowed down a likely vendor
(e.g. the CBBFE0E1 cluster's Xiaomi-OUI espruino lead).

Four cluster UUIDs are seeded into the parser today, each observed
across multiple exports:

| Cluster UUID | UUID version | Sightings | Notes |
|--------------|--------------|-----------|-------|
| `72DAA6C3-29C2-6283-0C4A-2818E4D37E75` | v6 (RFC 9562, reordered Gregorian time, June 2024) | 28 (× 2 exports) | Trailing `2818E4D37E75` is random output — OUI `28:18:E4` unassigned at IEEE |
| `3C586335-D0C8-5A32-9B53-1F8EB63C3C0B` | v5 (RFC 4122, SHA-1 name-based) | 24 (× 2 exports) | Trailing `1F8EB63C3C0B` is SHA-1 hash output, not a MAC; OUI `1F:8E:B6` unassigned |
| `CBBFE0E1-F7F3-4206-84E0-84CBB3D09DFC` | v4 (RFC 4122, random) | 476 (× 4 exports) | Largest single-device unattributed cluster. Vendor lead: surfaced on a Xiaomi-OUI (3C:BD:3E) device in espruino/3356 — possibly Mi-ecosystem accessory; unconfirmed. Exposed in `metadata.vendor_lead`. |
| `D839FC3C-84DD-4C36-9126-187B07255114` | v4 (RFC 4122, random) | 10 (× 4 exports × 2 devices) | Trailing OUI `18:7B:07` unassigned at IEEE — confirms random bits, not a MAC. No public attribution. |

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUIDs | exactly one entry, matching a cluster UUID | case-insensitive |
| Manufacturer data | *(none)* | |
| Service data | *(none)* | |
| Local name | *(none)* | |
| Address type | `random` | rotating private address |

### Match Rule

The advertised `serviceUUIDs` list contains a UUID that case-insensitively
matches an entry in the embedded `knownClusters` table. No other signals
are required (the absence of additional signal is itself characteristic).

### What We Can Surface

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Unknown` |
| `service_uuid` | matched cluster | lowercase canonical |
| `uuid_version` | UUID nibble | `5`, `6`, ... |
| `family_signature` | per-cluster | e.g. `uuidv5_3c586335`, `uuidv6_72daa6c3` |
| `verification_hint` | hard-coded | guidance for nRF Connect active scan + GATT DIS read |

### What We Cannot Surface from the Advertisement

- Vendor identity (by definition — these are unattributed clusters).
- Device class, model, firmware version, battery state, …
- Anything beyond "this UUID family is present nearby."

## Why a Version-Aware Cluster Parser?

UUIDv5 (SHA-1 name-based) and UUIDv6 (reordered Gregorian time) service
UUIDs are unusual in BLE. Most vendor service UUIDs are either:

- SIG 16-bit slots (`0xFFxx`, `0xFExx`), or
- 128-bit UUIDv1 (timestamp-based, easy node-byte forensics — see
  `vendor_2a2ae2dbcce4`), or
- 128-bit UUIDv4 (random — uninformative).

A v5 service UUID strongly suggests the vendor's SDK derives the UUID
deterministically from `(namespace, service_name)` — common when an
SDK ships pre-computed identifiers tied to logical service names. Even
without knowing the namespace, exposing `uuid_version=5` lets future
forensic passes group all v5-service-UUID devices for batch analysis.

A v6 service UUID is rare in any context — RFC 9562 only landed in
mid-2024 — so it implies a recent SDK or hand-rolled UUID generation.

## Stable Identity

Anchor identity on the **cluster** rather than per-device:

```
stable_key = unknown_derived_uuid_cluster:<family_signature>
identifier = SHA256(stable_key)[:16]
```

Two physical devices on different MACs that share a cluster UUID
collapse to the same identity — by design — because we have no way to
disambiguate them from the ad alone, and the value of this parser is
counting the cluster as a single family.

## Adding a New Cluster

1. Observe a recurring UUID-only signature across ≥2 exports.
2. Confirm the UUID is algorithmically derived (decode the version
   nibble; SHA-1 / Gregorian / random tell different stories).
3. Add the lowercase canonical UUID + a `family_signature` to the
   `knownClusters` table in `UnknownDerivedUUIDClusterParser`.
4. Register the UUID with the Pipeline so the registry routes ads to
   the parser.
5. Add a `@Test` case covering a real capture from the exports.

## Detection Significance

- Stable, recurring devices in the environment that we cannot yet
  attribute — useful as anchor points for cross-export deduplication
  and future ground-truth research (nRF Connect active scan, OUI
  resolution of the public-side MAC if it surfaces, GATT DIS read).
- Both seeded clusters are single-device, low-RSSI, long-dwell — fits
  fixed-installation smart-home accessories or building-system tags.

## References

- [RFC 4122 — UUID v1 / v3 / v4 / v5](https://datatracker.ietf.org/doc/html/rfc4122)
- [RFC 9562 — UUID v6 / v7 / v8](https://datatracker.ietf.org/doc/html/rfc9562)
- [IEEE OUI registry CSV](https://standards-oui.ieee.org/oui/oui.csv) (used to confirm `28:18:E4` and `1F:8E:B6` are unassigned)
- Sibling parsers: `Sources/Parsers/Static00E0BeaconParser.swift`,
  `Sources/Parsers/VendorNode2A2AE2DBCCE4Parser.swift`
