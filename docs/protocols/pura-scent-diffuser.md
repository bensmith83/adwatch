# Pura Smart Scent Diffuser Protocol

## Overview

**Pura Scents, Inc.** makes app-controlled plug-in fragrance diffusers
(Pura 3, Pura 4, Pura Plus, Pura Home/V5, Pura Car, Pura Mini). The
diffusers join Wi-Fi but keep a BLE radio advertising continuously for
onboarding, proximity/geofence hand-off and app re-discovery — so a
scanner in a home that uses them sees them constantly. In our corpus this
family was the **single highest-volume unparsed cluster**: 1 559 sightings
across 5 distinct units in one capture session.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0BD8` | SIG-assigned to *PURA SCENTS, INC.* — unique and uncollidable |
| Service UUID (gen A) | `EFFC7A09-9889-44B0-A80B-1EE079591945` | vendor 128-bit; co-advertised with the CID |
| Service UUID (gen B) | `9B2DBC93-928B-430E-9434-12C06001485C` | vendor 128-bit; co-advertised with the CID |
| Address type | random | |
| Device class | `scent_diffuser` | |

Neither 128-bit UUID appears in any public registry; both were only ever
observed alongside CID `0x0BD8`, never apart from it, and never on the
same unit as each other. The natural reading is **two hardware/firmware
generations** — but which retail model maps to which UUID is *not*
established, so the parser reports the UUID rather than naming a model.

## Ad Format

Two distinct manufacturer-data layouts were observed, one per service-UUID
generation.

### Generation A — 6-byte unit ID (service `EFFC7A09-…`)

One unit produced three frame lengths in the same session:

```
d8 0b | c7 c5 ba f9 57 f6                              (8 bytes,  ADV)
d8 0b | 4f 05 1b | c7 c5 ba f9 57 f6                   (11 bytes, SCAN_RSP)
d8 0b | c7 c5 ba f9 57 f6 | 4f 05 1b c7 c5 ba f9 57 f6 (17 bytes, merged)
```

The 17-byte form is CoreBluetooth's merge of the ADV and SCAN_RSP
manufacturer-data blocks (the second block's own `d8 0b` CID is dropped in
the merge). The invariant is the **6-byte unit ID** `c7 c5 ba f9 57 f6`,
which appears once or twice depending on which frames the scanner caught.

The ID is *not* an IEEE-registered MAC — byte 0 (`0xC7`) has the
locally-administered bit set, so it is a vendor-assigned identifier, not a
hardware address.

### Generation B — typed, 4-byte unit ID (service `9B2DBC93-…`)

```
d8 0b | 1c | 03 04 | 5e 69 2d ed                        (9 bytes)
d8 0b | 1c | 03 04 | 69 50 48 a2                        (9 bytes)
d8 0b | 1c | 03 04 | 00 a7 6f d0                        (9 bytes)
d8 0b | 1b | 07 16 | 66 76 92 17 | 00 00 00 00 00       (14 bytes)
```

| Bytes | Meaning | Evidence |
|-------|---------|----------|
| 0–1 | CID `0x0BD8` (LE `d8 0b`) | all records |
| 2 | frame type: `0x1C` (3 units) or `0x1B` (1 unit) | |
| 3–4 | type-dependent constants: `03 04` with `0x1C`, `07 16` with `0x1B` | |
| 5–8 | 4-byte per-unit identifier | distinct on every unit |
| 9–13 | trailing bytes, all zero (`0x1B` frame only) | 1 unit — surfaced, not asserted |

The per-unit tail was byte-stable across the whole capture for each unit
(e.g. `5e 69 2d ed` on every one of that unit's sightings), so it is a
device identity field, not a counter or a sensor reading.

## What We Cannot Parse

- Fragrance vial identity / scent name (Pura's vials carry an NFC tag read
  by the diffuser, not broadcast over BLE)
- Intensity / schedule / on-off state
- Vial fill level
- Room or account association
- Firmware version

Nothing observed changes with diffuser activity — the advertisement is a
pure discovery beacon.

## Identity Hashing

Prefer the embedded per-unit identifier over the (random, rotating) BLE
address:

```
if unit id present:
    identifier = SHA256("pura:{unit_id_hex}")[:16]
else:
    identifier = SHA256("pura:{mac}")[:16]
```

## Detection Significance

A sighting means a Pura diffuser is plugged in and powered within BLE
range. Because the unit ID is stable and broadcast in the clear while the
BLE address rotates, the ID defeats the address-rotation privacy measure:
a passive observer can re-identify the same household device across
sessions. Worth noting, not alarming — it is a plug-in air freshener, not
a wearable.

## Confidence / Attribution

**High for the vendor, deliberately silent on the model.** CID `0x0BD8` is
SIG-assigned solely to Pura Scents, Inc.; 5 distinct units and 1 559
sightings corroborate a real, recurring device rather than a one-off; two
consistent internal layouts each pair 1:1 with a vendor 128-bit service
UUID. What is *not* claimed: which Pura product generation each layout
belongs to, and the meaning of the frame-type/constant bytes.

## References

- Bluetooth SIG `company_identifiers.yaml` — `0x0BD8 = PURA SCENTS, INC.`
- [Pura product line](https://pura.com/products/device) — Pura 4, Pura
  Plus, Pura Home and the rest of the current diffuser range
