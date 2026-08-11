# VELUX BLE remote control (model unconfirmed)

## Overview

VELUX A/S — the Danish manufacturer of motorized skylights and roof
windows, which ship BLE remote controls — holds Bluetooth SIG company ID
`0x06E7`. Two distinct physical units were captured (2026-07-29, 70 total
sightings), both also advertising the standard GATT service-UUID set
`1802` (Immediate Alert) + `180F` (Battery) + `180A` (Device Information) +
`1812` (HID) — a coherent, recognizable battery-remote profile that
corroborates the CID beyond a bare registry match.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x06E7` | VELUX A/S, SIG-assigned |
| Service UUIDs | `1802`, `180F`, `180A`, `1812` | Standard SIG profile: Immediate Alert, Battery, Device Information, HID — the `1812` (HID) UUID is required as part of the identification gate alongside the CID |

### Advertisement data

13-byte manufacturer data, byte map (both observed units):

```
e7 06 | XX XX | 00 00 00 00 20 | XX | XX | XX | 17
CID    [2..4)  [4..9) constant  [9] [10] [11] [12] constant
```

`[2..4)` and `[9..12)` are per-unit fields (stable within each unit across
its whole observation window — not live status/counter data, at least not
observably so with only two units and short windows of 92 minutes / 4h50m).

### Parser gate

Requires the `1812` service UUID present alongside the manufacturer-data
match. One corpus record shares unit A's exact manufacturer-data payload
but carries no service UUIDs at all — a weaker-evidence duplicate of an
already-covered payload, deliberately excluded from matching.

### What we can extract

| Field | Notes |
|-------|-------|
| `unit_field_hex` | `[2..4)`, distinguishes the two observed physical units |
| `status_byte9_hex`, `status_byte10_hex`, `status_byte11_hex` | Per-unit, stable-within-unit; semantics unconfirmed |

### What we cannot extract

- The specific VELUX product/model (no local name on any record) — ships
  with `attribution_confidence: "moderate"` in parser metadata
- Whether the varying fields are ever live (only observed as stable
  within-unit, in short windows)

## Detection significance

- A real consumer BLE remote, not a beacon — the SIG service-UUID
  corroboration (a legitimate HID+battery profile) is meaningfully
  stronger evidence than a bare CID match alone.

## References

- Bluetooth SIG company-identifier registry (VELUX A/S, `0x06E7`).
- Bluetooth SIG GATT service assignments (`1802`, `180F`, `180A`, `1812`).
- Captures: `research/telemetry-merged.json`, 2026-07-30 sweep
  (`research/sweep-2026-07-30-candidates.md` in the app repo).
