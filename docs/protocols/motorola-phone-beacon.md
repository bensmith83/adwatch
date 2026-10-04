# Motorola Phone Presence Beacon (service data 0x5246 "RF" + 0x0720)

## Overview

Recent Motorola phones broadcast a small BLE presence beacon made of two
service-data blocks under **non-SIG 16-bit UUIDs**: a fixed 20-byte device
token under `0x5246` — whose two bytes spell ASCII `RF` — and the phone's
own Bluetooth name under `0x0720` in the scan response. The name observed
was `moto g stylus - 2025`, Motorola's factory `moto <line> - <year>`
device-name format, which is what makes the vendor attribution solid.

`RF` reads as Motorola's **Ready For** cross-device feature (since folded
into **Smart Connect**), whose desktop and tablet apps discover nearby
Motorola phones over BLE before connecting. That reading is an inference
from the mnemonic and the beacon's behaviour; no Motorola document
describing the frame was available to the sweep, so the feature name is
recorded as a hypothesis, not a decode.

First captured in the 2026-08-27 telemetry sweep: one phone, 4 records /
222 sightings across two random-address rotations inside an 8-minute window,
RSSI up to −69 dBm.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service data | under `0x5246` | exactly 20 bytes; present in every record |
| Service data | under `0x0720` | NUL-padded ASCII Bluetooth name; scan response only (2 of 4 records) |
| Service UUID (16-bit list) | `0x5246` | advertised alongside the service data |
| Company ID | none | no manufacturer-specific data |
| Local name | none | the name travels in the `0x0720` block instead |
| Address | random | rotated inside the capture while both blocks stayed constant |

Neither `0x5246` nor `0x0720` is a Bluetooth SIG allocation (checked
against the SIG `member_uuids.yaml` and `service_uuids.yaml`, 2026-08-27).
`0x5246` = ASCII `R` `F`. `0x0720` has no obvious mnemonic.

### Frame layout

**`0x5246` — device token (20 bytes)**

| Offset | Field | Size | Notes |
|--------|-------|------|-------|
| 0–19 | device token | 20 | byte-identical across all four records and both BLE addresses; SHA-1-sized, high-entropy — reads as a hashed device identifier. Not decoded. |

**`0x0720` — Bluetooth name (variable, 27 bytes observed)**

| Offset | Field | Size | Notes |
|--------|-------|------|-------|
| 0–n | name | ≥ 1 | printable ASCII, the phone's Bluetooth name |
| n+1– | padding | rest | `0x00` fill (7 bytes observed after a 20-character name) |

### Examples (real bytes; the token is synthetic — see Privacy)

```
0720: 6d 6f 74 6f 20 67 20 73 74 79 6c 75 73 20 2d 20 32 30 32 35 00 00 00 00 00 00 00
      "moto g stylus - 2025"                                       NUL padding

5246: 20 bytes, constant per phone (real value withheld)
```

## Parser Scope (passive-only)

`motorola_phone_beacon` claims an advertisement when `0x5246` service data
is present and exactly 20 bytes long. A `0x0720` block on its own is never
claimed. It reports:

| Field | Source |
|-------|--------|
| `vendor` | `Motorola Mobility` |
| `product_family` | `Motorola smartphone` |
| `service_uuid`, `service_uuid_ascii` | `5246`, `RF` |
| `device_token_hex` | the 20-byte token — tagged **unique, stable** |
| `name_service_uuid` | `0720` when that block is present |
| `advertised_name` | the decoded name — tagged **personal** (it is user-editable) |
| `model` | the name, only when it matches Motorola's factory pattern (`moto`, `motorola`, `edge`, `razr`, `thinkphone` …) — tagged model-identifying |
| `name_block_hex` | the raw `0x0720` bytes when they are not a printable NUL-padded name |
| `attribution` | `self_reported_name` when a factory-pattern name is present, else `service_uuid_fingerprint` |
| `attribution_note` | the Ready For / Smart Connect inference, spelled out as such |

Identity is keyed on the token (`stableKey = motorola_phone_beacon:<token>`),
which survived the address rotation inside the capture. Whether it also
survives a reboot or a Bluetooth reset is unknown at n = 1 phone / 8
minutes; the stable tag is the privacy-conservative reading and keeps the
value out of telemetry uploads. Device class `phone`.

## Privacy

A phone that randomises its BLE address and then broadcasts a fixed
20-byte token — plus its model name in the scan response — is trackable
across address rotations by anyone listening, for as long as the token
persists. That is why the token is the identity anchor here, and why the
real token is not reproduced in this document or in the app's test
fixtures.

## What We Cannot Parse

- What the token is derived from (a device id, a Bluetooth address hash, an
  account-bound key) and how often, if ever, it re-mints.
- Which feature emits the beacon. Ready For / Smart Connect is the working
  hypothesis; confirming it needs a Motorola phone with the feature toggled
  on and off, or the Smart Connect app's discovery code.
- Whether other Motorola lines (edge, razr) use the same two UUIDs. The
  parser's name pattern admits them, but only `moto g stylus - 2025` has
  been observed.

## References

- NearSight `research/sweep-2026-08-27-candidates.md` — the capture and the
  attribution reasoning
- [Bluetooth SIG member service UUIDs](https://bitbucket.org/bluetooth-SIG/public/raw/HEAD/assigned_numbers/uuids/member_uuids.yaml) — `0x5246` / `0x0720` not assigned
- Motorola Smart Connect (formerly Ready For) — cross-device feature whose
  desktop app discovers phones over BLE; the `RF` mnemonic's presumed origin
