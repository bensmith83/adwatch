# Google/Android Nearby BLE Protocol (FEF3)

## Overview

Android phones broadcast BLE advertisements using service UUID `0xFEF3` as part of Google's Nearby/presence system. The payload is encrypted and cannot be parsed beyond identification. This is one of the highest-volume BLE advertisement types in any environment with Android phones.

## Identifiers

- **Service UUID:** `0xFEF3` (Google LLC)
- **Device class:** `phone` (Android)

## Service Data Format (UUID `fef3`)

Two observed frame types:

### Type 1: Long frame (prefix `4a17`, 26 bytes)

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0-1 | 2 | Magic | `4a17` — frame type identifier |
| 2 | 1 | Length? | `0x23` (35 decimal) consistently |
| 3-6 | 4 | Device hash | ASCII-like chars, e.g. `4a545741` = "JTWA" |
| 7-8 | 2 | Unknown | `1132` consistent across all samples |
| 9-25 | 17 | Encrypted payload | Varies per ad, likely encrypted with device key |

### Type 2: Short frame (prefix `1101`, 6-10 bytes)

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0-1 | 2 | Magic | `1101` or `1102` |
| 2-5 | 4 | Encrypted ID | Rotating identifier |
| 6-9 | 0-4 | Extended data | Present in `1102` variant |

## Sample Data

```
Long (4a17 prefix):
  4a17234a54574a1132653328bfc6bac83e76863639467e2e3eb682
  4a172347314b4a11324423972396954d36ed62a4c334e4dde6ac51

Short (1101 prefix):
  1101a13a95ab
  1101cee5d60e

Short (1102 prefix):
  1102e41d37c329fa0d09
```

## Volume

This is extremely high volume — 66 ads in a small sample. In any environment with Android phones, expect hundreds to thousands of these per hour.

## Parsing Strategy

1. Match on service_uuid `fef3`
2. Identify frame type from first 2 bytes (`4a17` = long, `1101`/`1102` = short)
3. Report as "Android Nearby device" with frame type
4. **Do not attempt to decrypt** — Google proprietary encryption

## Known Limitations

- Fully encrypted — no useful data beyond "an Android phone is nearby"
- Rotating identifiers prevent tracking
- No official documentation
- High volume = potential noise in results

## References

- Bluetooth SIG UUID `0xFEF3` — Google LLC
- Google Nearby Connections API (application layer, not this advertisement format)
- https://developers.google.com/nearby
