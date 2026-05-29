# `uac<3 digits>` tracker (vanity CID 0x5654)

## Overview

Single physical unit captured 186 times in one export session. Local name `uac088`. Company ID `0x5654` is not assigned by the Bluetooth SIG — the on-wire bytes are ASCII "TV" / "VT" stuffed into the CID slot, the same vanity-CID trick documented in `VictronEnergyParser` (`"VE"`) and `FHPSmartFanParser` (`"WF"`). Vendor unconfirmed.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x5654` | ASCII "VT" / "TV" — not SIG-assigned |
| Local name | `uac<3 digits>` | e.g. `uac088`. Optional but if present must match this pattern |
| Manufacturer data length | 9 bytes (CID + 7 payload) | Strict shape lock |

### Manufacturer data layout

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| 0 | 2 | Company ID | `54 56` (LE → 0x5654) |
| 2 | 1 | Frame version | Always `0x02` in captures |
| 3 | 1 | State byte | Observed `0x81`, `0x7e` |
| 4 | 5 | Rolling counter | Changes between consecutive ads |

### Captured frames

| local name | mfg data |
|------------|----------|
| `uac088` | `54 56 02 81 61 5a 94 36 38` |
| `uac088` | `54 56 02 81 61 67 94 36 38` |
| `uac088` | `54 56 02 7e 61 5d 92 37 34` |

### What We Can Parse

- Vendor presence on the vanity CID
- `unit_id` (3 digits from the local name)
- `state_byte` and `rolling_counter_hex` for downstream analysis

### What We Cannot Parse

- Vendor / SKU (unconfirmed)
- Semantic meaning of `state_byte`
- Stable per-device serial beyond the local-name unit ID

## Detection significance

- Surfaces a frequently-broadcasting unidentified tracker in the user's environment.
- Vanity CID + tight 9-byte shape lock keeps the parser specific despite the CID not being claimed by SIG.

## References

- Bluetooth SIG `company_identifiers.yaml` (0x5654 unassigned).
- Captures: `research/adwatch_export 8.json`.
