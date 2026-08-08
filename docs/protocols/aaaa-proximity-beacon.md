# 0xAAAA service-data proximity beacon

## Overview

A proximity-beacon payload carried in **service data under the 16-bit UUID
`0xAAAA`**, rather than in the manufacturer-data envelope iBeacon uses. The
layout is the familiar one — a 16-byte proximity UUID plus a 16-bit device ID
— just relocated to a different advertisement field.

The corpus contains a single dense deployment: 68 distinct units heard from one
spot inside a 2.5-minute window, each with a fixed ID in the range `0x0631`–
`0x0789` and all sharing one 16-byte UUID.

**No vendor is claimed.** `0xAAAA` is not SIG-assigned, the co-advertised
`0xFFF1` is the generic TI-style "simple profile" UUID shipped by dozens of
commodity BLE modules, and the proximity UUID itself is plainly a hand-typed
installer/SDK default (`AAA0 BBB0 CCC0 DDD0 ABCD …`) that was never changed —
not a vendor-allocated namespace. The doc and parser are named for the wire
shape.

## Supported models

Unknown. What is known about the observed population:

| Property | Value |
|----------|-------|
| Units in the one observed deployment | 68 |
| Device-ID range | `0x0631`–`0x0789` (68 of ~344 possible values heard) |
| Proximity UUID | `AAA0BBB0-CCC0-DDD0-ABCD-E333B45E0006` |
| Address type | random, one stable address per unit for the capture |
| Local name | none, on any unit |

## BLE Advertisement Format

### Identification anchors

| Signal | Value | Notes |
|--------|-------|-------|
| Service data UUID | `0xAAAA` | Not SIG-assigned |
| Service data length | exactly 20 bytes | 68/68 captures |
| Co-advertised service UUID | `0xFFF1` | Present in 68/68 — recorded, **not** used for routing |

`0xFFF1` is deliberately not a routing key: it is generic enough that
registering on it would drag in a large unrelated population.

### Byte map

```
aaa0bbb0 ccc0 ddd0 abcd e333b45e0006 | II II | ba 64
└────────────────┬──────────────────┘ └──┬──┘ └──┬──┘
    16-byte proximity UUID             dev ID  const
```

| Bytes   | Field | Notes |
|---------|-------|-------|
| [0-15]  | Proximity UUID | Byte-identical in 68/68 records |
| [16-17] | 16-bit big-endian device ID | Unique and stable per unit; 68 distinct values observed |
| [18-19] | `ba 64` | Constant in 68/68 — reported raw, see below |

### Deliberately not decoded

The constant tail `ba 64` invites a reading as measured-power (`0xBA` = −70 dBm
as int8) plus battery (`0x64` = 100 %), both of which are plausible beacon
defaults. The two bytes **never vary across 68 devices**, so the capture
contains exactly zero evidence discriminating that reading from "two more
constants". Claiming it would be a guess dressed as a decode. Reported raw.

### Ruling out an advertisement flood

68 near-identical adverts appearing inside 2.5 minutes is also what a single
BLE-spam transmitter cycling random addresses looks like, so that had to be
excluded before treating the cluster as real devices.

Test: a rotating counter driven by one radio would climb monotonically with
capture time. It does not.

- Values from across the entire `0x0631`–`0x0789` range appear within the
  **first two seconds** of the capture.
- Each `deviceIdentifier` holds **one fixed value** for its entire lifetime.
- 36 of the 68 persist 100–152 s — the full scan window — at 4–17 sightings
  each.

That is 68 static transmitters with fixed IDs, i.e. a dense installed fleet
heard from one location, not a flood.

### What we can extract

| Field | Notes |
|-------|-------|
| `proximity_uuid` | Canonical 8-4-4-4-12 form |
| `device_id`, `device_id_hex` | Per-unit identity |
| `trailing_hex` | Bytes [18-19], raw |
| `deployment` | `known_template` for the observed UUID, `unrecognized` otherwise |
| `service_uuid` | `aaaa` |

### What we cannot extract

- Vendor, module family, or SKU.
- What the deployment is *for*. The ID space and density are consistent with
  asset tags, shelf labels, or room/zone beacons, but nothing in the payload
  distinguishes those.
- Any telemetry: there is no varying field in the frame besides the per-unit
  ID.

## Parser scope

Passive advertisement decoding only. No connection, no GATT reads, no writes.

The 20-byte UUID + ID layout is the structural claim; the specific proximity
UUID is **not** required to match, so a second deployment of the same module
family still decodes (flagged `deployment = unrecognized`).

## Detection significance

- Largest zero-route cluster of the 2026-08-08 sweep by record count: 68 of the
  133 new candidate signatures (51%).
- A dense multi-unit beacon deployment is a meaningful thing to surface to a
  user: it says something about the *place* they are standing in, not just
  about one device.
- Identity is derived from the payload (UUID + device ID) rather than the BLE
  address, so units correlate correctly if their random addresses rotate.

## Confidence and attribution

**High for the structure, none for the vendor.** The byte map is verified
against all 68 records with no exceptions, and the fleet-vs-flood question was
tested rather than assumed. But every identifying signal in this advertisement
is a generic default — an unassigned service UUID, a commodity profile UUID,
and a placeholder proximity UUID — so there is no honest vendor claim to make.

Note there is **no collision** with the `Stryd` parser, which is registered on
*manufacturer* company ID `0xAAAA`. This cluster carries no manufacturer data
at all; the shared `AAAA` value sits in a different advertisement field.

## References

- Bluetooth SIG 16-bit UUID registry (confirms `0xAAAA` is unassigned).
- Not to be confused with `afero-platform-device.md`, which documents the
  other cluster examined in the same sweep (CID `0x02D2`). That one was
  withdrawn as a duplicate — it had already been documented by the 2026-08-01
  sweep.
- Captures: 68 records, 2026-08-08 01:11:33–01:14:06 UTC, via
  `research/telemetry-merged.json`; analysis in the app repo at
  `research/sweep-2026-08-08-candidates.md`.
- Parser: `Sources/Parsers/AAAAProximityBeaconParser.swift`
  (`aaaa_proximity_beacon`).
