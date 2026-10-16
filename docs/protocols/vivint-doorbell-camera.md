# Vivint BLE Beacons (CID 0x0DE8): Doorbell Camera Pro (Gen 2) and a TEST-frame product

## Overview

**Vivint, Inc.** is a US smart-home security company. Company identifier
`0x0DE8` is SIG-registered to Vivint, Inc. Its **Doorbell Camera Pro
(Gen 2)** — retail model `VS-DBC350-WHT` (vendor quick-reference manuals
cover CypressWiFi and QualcommWiFi board variants) — emits a small BLE
manufacturer-data beacon. The CID carries **two products**: the doorbell's
unit-id frame, and an ASCII `TEST` frame from a second Vivint product that
nothing names yet (see Variant B).

The capture behind this doc: **19 records / 132 sightings across 11 days,
2026-06-05 → 2026-10-05** (full-history corpus). The 2026-08-23 sweep saw
only the ASCII `TEST` frame and one `01 01 01` frame and deferred the
cluster as "dev/installer firmware; n=1-2". The named anchor below plus
seven distinct unit ids since then close that gap.

**Attribution / confidence: high.** Two independent signals: the SIG CID
is Vivint's own slot, and a self-labelled record (`DBC350_E1:63:84`)
embeds the same two MAC octets its payload carries. The model claim rides
on that single named capture — other Vivint products could share the
`01 01 01` shape, so the parser reports the shape's model with that
provenance noted. The `TEST` frame carries no model claim: it is
attributed to Vivint (the CID) and nothing more.

## Supported Models

| Model | Marketing name | Evidence |
|---|---|---|
| VS-DBC350-WHT | Vivint Doorbell Camera Pro (Gen 2) | named corpus record `DBC350_E1:63:84` |
| unidentified | second Vivint product (`TEST` frame) | CID `0x0DE8`; co-advertises its own 128-bit service UUID, distinct from the doorbell's |

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Company ID | `0x0DE8` (LE wire bytes `0d e8`) — Vivint, Inc. |
| Manufacturer-data total length | 8 bytes (2-byte CID + 6-byte payload) |
| Payload variant A prefix | `01 01 01`, trailing byte `00` |
| Payload variant B | `54 45 53 54 00 00` (ASCII "TEST") |
| Local name | `DBC350_<MAC suffix>` when captured; usually absent |
| Co-advertised service UUID | `0939EB10-D9A5-411D-8EC0-EEB89AF1E418` with variant A; `C5B2544E-7597-49B2-90E2-49EAC275DEED` with variant B |
| Address type | random |

Match rule: CID `0x0DE8` **and** 6-byte payload **and** (variant A prefix
with trailing `00` **or** the exact "TEST\0\0" body). The service UUID
is recorded when present, never required: a sighting can miss it.

### Manufacturer Data Structure

#### Variant A — unit-id frame (10 records, 7 distinct unit ids)

```
0d e8 01 01 01 63 84 00
^^^^^ ^^^^^^^^^ ^^^^^ ^^
CID   prefix    id    00
```

| Offset (payload) | Length | Value | Description |
|---|---|---|---|
| 0–2 | 3 | `01 01 01` | frame prefix (constant, 10/10 records) |
| 3–4 | 2 | varies | unit id — the low two octets of the unit's own MAC, in display order. Anchor: name `DBC350_E1:63:84` ↔ payload `63 84` |
| 5 | 1 | `00` | constant |

Unit ids observed: `6384` (named), `8bdf`, `dcf8` (48 sightings over two
records), `e9f0`, `2c51`, `3954`, `5413`.

#### Variant B — `TEST` frame, a second Vivint product (9 records / 61 sightings)

```
0d e8 54 45 53 54 00 00
^^^^^ ^^^^^^^^^^^ ^^^^^
CID   "TEST"      00 00
```

The TEST variant shares CID, total length and trailing zeros with variant
A, but it is not the doorbell in a factory or test mode. In the raw
uploads every TEST frame co-advertises `C5B2544E-7597-49B2-90E2-49EAC275DEED`,
while every unit-id frame (and the one device sending a third shape,
`01 00 42 ff ff 00`) co-advertises `0939EB10-D9A5-411D-8EC0-EEB89AF1E418`.
The devices carrying each are disjoint (8 and 8, none shared), and TEST
turns up on six uploading phones from 2026-08-15 to 2026-10-06, so it is
not a one-off bench unit. No named record ties it to a product: it is
reported as `frame_variant = test_marker` under the same parser, at
vendor level only (`vendor = Vivint`, device class `smart_home`, no
model). The `01 00 42 ff ff 00` shape is left unclaimed.

## Parser Scope

Passive observation only (`vivint_doorbell`):

- Extracts: frame variant (`unit_id` / `test_marker`), unit id (variant
  A), model (variant A, with anchor provenance), and the co-advertised
  Vivint service UUID as `vivint_service_uuid` when present.
- Device class: `doorbell_camera` for variant A, `smart_home` for
  variant B.
- **Identity keys on the BLE address** and sets no `stableKey`: the 2-byte
  unit id is a fragment of the factory MAC — a 65,536-value space shared
  by every DBC350 — too short to key on. It rides along in metadata as a
  re-identification candidate.

### What We Cannot Parse

- No telemetry (no battery, no event/motion state) is present in either
  variant; this is a presence beacon.
- Live video / settings require the Vivint panel ecosystem (Wi-Fi), not
  BLE GATT.

## References

- Vivint `VS-DBC350-WHT` Quick Reference (Doorbell Camera Pro Gen 2),
  vivintcdn.com (CypressWiFi / QualcommWiFi variants).
- research/sweep-2026-10-06-candidates.md (nearsight-app repo) — cluster
  evidence and the 2026-08-23 deferral note.
