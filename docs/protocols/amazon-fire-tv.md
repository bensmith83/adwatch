# Amazon Fire TV BLE Protocol

## Overview

Amazon Fire TV devices (Stick, Cube, smart TVs) broadcast BLE advertisements using service UUID `0xFE00`. The protocol is proprietary and undocumented.

## Identifiers

- **Service UUID:** `0xFE00` (Amazon.com Services, Inc.)
- **Local name:** `Fire TV`
- **Device class:** `streaming_device`

## Service Data Format (UUID `fe00`)

20-22 bytes:

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0 | 1 | Header | Always `0x00` |
| 1-9 | 9 | Device identifier | Rotating/hashed — varies per device |
| 10-13 | 4 | Device type? | `4b4b4463` seen on 20-byte ads, `46504273` on 22-byte ads |
| 14-15 | 2 | Version? | `0001` |
| 16-17 | 2 | Flags | `02` + padding |
| 18-21 | 0-4 | Extended | Present in 22-byte variant, `0001` observed |

## Sample Advertisements

```
Fire TV (20 bytes):
  00092f06a181b65da3907bc10a 4b4b4463 000102
  00dc9571f10df6b403d047c993 4b4b4463 000102

Fire TV (22 bytes):
  00cf3bdbf5a2f2c2b05a1669a6 46504273 0001020001
```

### Observations

- First byte always `0x00`
- Bytes 1-9 appear to be a device-specific hash (different per Fire TV unit)
- Bytes 10-13 may encode device model:
  - `4b4b4463` = "KKDc" (ASCII) — possibly Fire TV Stick
  - `46504273` = "FPBs" (ASCII) — possibly Fire TV Cube or different model
- Trailing bytes `000102` are consistent

## Parsing Strategy

1. Match on service_uuid `fe00` OR local_name `Fire TV`
2. Extract device type bytes at offset 10-13
3. Map known type codes to models (needs more samples)
4. Report device class, model hint, presence

## Known Limitations

- Amazon proprietary protocol — no official documentation
- Device type mapping is speculative (need more samples from different Fire TV models)
- Rotating identifiers in bytes 1-9

## References

- Bluetooth SIG UUID `0xFE00` — Amazon.com Services, Inc.
- Amazon Fire TV developer documentation (no BLE protocol details)
