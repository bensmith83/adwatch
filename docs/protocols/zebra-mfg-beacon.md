# Zebra Technologies manufacturer-data beacon (device type unconfirmed)

## Overview

A second, unrelated Zebra Technologies BLE signal from the one documented
in `zebra.md` (the FE79 service-UUID barcode-scanner protocol). This one is
manufacturer-data based, keyed on Zebra's SIG-assigned company ID `0x01F1`
(code 497) — corroborated against both an external company-identifier
registry snapshot and this project's own vendored
`Tests/RegistryTests/Fixtures/company_identifiers.yaml`. Every corpus
sighting (49 records, 2026-07-29) traces back to the same single physical
unit; no local name or service UUID accompanies any of them, so the exact
Zebra product (scanner, printer, mobile computer) is **not** identified —
only that it's a genuine Zebra-CID device.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x01F1` | Zebra Technologies Corporation, SIG code 497 |
| Constant device-ID block | `c1 ad 93 36 12 92 cc 00 49 64 15 59 54 95 45 84` at bytes `[2..18)` | Identical across all 49 records; bytes `[2..8)` in particular look like a re-embedded MAC fragment |

### Frame variants

Two lengths observed, byte-for-byte verified across all 49 records:

**Short (27 bytes)**

```
f1 01 | <16-byte const device-ID block> | XX | XX | XX | 00 bf | XX | XX | ff b0
CID    [2..18)                          [18] [19] [20] [21..23) [23] [24] [25..27)
```

**Long (54 bytes)** — short's 27 bytes, plus:

```
cd 04 10 41 2c 90 40 19 02 1a 93 36 12 02 | <6-byte two-state trailer> | 00 00 30 01 25 00 00
[27..41) constant                          [41..47)                     [47..54) constant
```

The `[41..47)` trailer region has been observed in exactly two states so
far (n too small to characterize further).

### What we can extract

| Field | Notes |
|-------|-------|
| `frame_size` | `short` / `long` |
| `status_byte18_hex`, `counter_byte19_hex`, `flags_byte20_hex` | Vary per-sighting within the short frame's `[18..21)` region; semantics unconfirmed |
| `status_byte23_hex`, `flags_byte24_hex` | Vary per-sighting within `[23..25)`; semantics unconfirmed |
| `trailer_state_hex` | Long frame only, `[41..47)` |

### What we cannot extract

- The specific Zebra product / device class (no name, no service data —
  hedged as `device_class: "unknown"` rather than guessed)
- Confirmed semantics for any of the varying byte fields (no corroborating
  documentation found for this frame shape)

## Detection significance

- Confirms a genuine Zebra Technologies device is present via a completely
  independent signal from the existing FE79 barcode-scanner detection —
  useful if a Zebra device doesn't advertise the FE79 service (e.g. a
  different product line, or a scanner in a mode that omits it).

## References

- Bluetooth SIG company-identifier registry (Zebra Technologies
  Corporation, code 497 / `0x01F1`).
- Captures: `research/telemetry-merged.json`, 2026-07-30 sweep
  (`research/sweep-2026-07-30-candidates.md` in the app repo).
