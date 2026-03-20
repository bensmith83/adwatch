# LG webOS TV BLE Protocol

## Overview

LG TVs running webOS broadcast BLE advertisements using LG's company ID and service UUID `0xFEB9`. The local name contains the TV model information.

## Identifiers

- **Company ID:** `0x00C4` (LG Electronics)
- **Service UUID:** `0xFEB9` (LG Electronics)
- **Local name pattern:** `[LG] webOS TV *`
- **Device class:** `tv`

## Manufacturer Data Format

9 bytes total:

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0-1 | 2 | Company ID | `0x00C4` (LE: `c400`) |
| 2 | 1 | Flags/version | `0x02` or `0x01` observed — possibly protocol version or mode |
| 3 | 1 | Status byte | `0x34` consistent across samples |
| 4-5 | 2 | Unknown | `0x1513` — possibly model category |
| 6 | 1 | Unknown | `0x17` |
| 7-8 | 2 | State/ID | `0xFD80` — possibly device state or hash |

## Sample Advertisements

```
[LG] webOS TV UT8000AUA:
  Company ID: 0x00C4
  Service UUID: FEB9
  Manufacturer data: c4000234151317fd80

  Breakdown:
    c400    company ID (LG)
    02      flags (version?)
    34      status
    1513    category
    17      unknown
    fd80    state/ID

Unnamed variant:
  Manufacturer data: c4000134151317fd80
  (byte 2 = 0x01 instead of 0x02)
```

## Parsing Strategy

1. Match on company_id `0x00C4` OR service_uuid `feb9`
2. Extract model name from local_name (strip `[LG] webOS TV ` prefix)
3. Parse flags byte at offset 2
4. Report TV model, presence, device class

## Model Extraction

Local name format: `[LG] webOS TV {model}`

Example: `[LG] webOS TV UT8000AUA` → model `UT8000AUA`

## References

- Bluetooth SIG Company ID `0x00C4` — LG Electronics
- Bluetooth SIG UUID `0xFEB9` — LG Electronics
- LG webOS BLE pairing documentation (limited)
