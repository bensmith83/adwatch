# Samsung Galaxy Buds BLE Protocol

## Overview

Samsung Galaxy Buds (Buds, Buds+, Buds Pro, Buds2, Buds3, Buds3 Pro, Buds FE) broadcast BLE advertisements using service UUID `0xFD69`. The local name contains the model and a device identifier suffix.

## Identifiers

- **Service UUID:** `0xFD69` (Samsung Electronics)
- **Local name pattern:** `Galaxy Buds*`
- **Device class:** `earbuds`

## Service Data Format (UUID `fd69`)

15 bytes observed:

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0 | 1 | Frame type | `0x00` observed |
| 1-2 | 2 | Device ID | `0x5fe6` in sample — likely model identifier |
| 3 | 1 | Flags | `0xf7` — bitfield, possibly connection/wearing state |
| 4 | 1 | Battery/state | `0x40` — likely left bud battery or combined state |
| 5 | 1 | Battery/state | `0x80` — likely right bud battery |
| 6 | 1 | Battery/state | `0xc9` — likely case battery |
| 7-14 | 8 | Device address / hash | Rotating identifier for anti-tracking |

## Sample Advertisements

```
Galaxy Buds3 Pro (E757) LE:
  Service UUID: FD69
  Service data: 005fe6f74080c94e5ded74a54e4000

  Breakdown:
    00          frame type
    5fe6        model/device ID
    f7          flags
    40          battery/state byte 1
    80          battery/state byte 2
    c9          battery/state byte 3
    4e5ded74    rotating ID part 1
    a54e4000    rotating ID part 2
```

## Model Identification

The local name format is: `Galaxy Buds{model} ({identifier}) LE`

| Name Pattern | Model |
|-------------|-------|
| `Galaxy Buds3 Pro` | Buds3 Pro (2024) |
| `Galaxy Buds3` | Buds3 (2024) |
| `Galaxy Buds2 Pro` | Buds2 Pro (2022) |
| `Galaxy Buds Pro` | Buds Pro (2021) |
| `Galaxy Buds FE` | Buds FE (2023) |
| `Galaxy Buds Live` | Buds Live (2020) |

## Parsing Strategy

1. Match on service_uuid `fd69` OR local_name containing `Galaxy Buds`
2. Parse model name from local_name
3. Extract service data fields if present
4. Report model, device class, and any decodable state/battery info

## Known Limitations

- Battery level encoding not fully confirmed — needs more samples across charge states
- Rotating identifiers prevent device tracking (by design)
- Samsung proprietary — no official BLE documentation

## References

- Samsung Galaxy Buds Plugin for Gadgetbridge: https://codeberg.org/Freeyourgadget/Gadgetbridge
- Bluetooth SIG UUID `0xFD69` — Samsung Electronics
- Community reverse engineering of Galaxy Wearable protocol
