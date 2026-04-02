# Razer BLE Protocol

## Overview

Razer gaming peripherals broadcast BLE advertisements using Razer's assigned service UUID `0xFD65`. Razer devices include wireless speakers, headsets, and mobile gaming accessories. The BLE advertisement format is not publicly documented.

## Identifiers

- **Service UUID:** `0xFD65` (16-bit, assigned to Razer Inc.)
- **Local name:** Product names (e.g. "Razer Lev3", "Razer Barracuda", "Razer Kishi")
- **Device class:** `gaming_peripheral`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFD65` | Razer Inc. assigned UUID |
| Local name | `Razer *` | Product name with Razer prefix |

### Manufacturer Data Format

12 bytes observed, company_id varies by product:

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0-1 | 2 | Company ID | Varies; product-dependent |
| 2-3 | 2 | Prefix | `8e06` observed |
| 4-11 | 8 | Payload | Device-specific, undocumented |

The manufacturer data format is proprietary and not publicly documented. The `8e06` prefix has been observed but its meaning is unknown.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid or local_name | Razer device nearby |
| Product name | local_name | Full product name |
| Product type | local_name | Speaker, headset, controller, etc. |

### What We Cannot Parse (undocumented)

- Battery level
- Firmware version
- Chroma RGB lighting state
- Connection mode (BLE vs. 2.4GHz dongle)
- Audio codec in use
- Manufacturer data payload meaning

## Known Products

| Local Name | Product | Category |
|-----------|---------|----------|
| `Razer Lev3` | Razer Leviathan V3 | Desktop speaker |
| `Razer Barracuda` | Razer Barracuda | Wireless headset |
| `Razer Barracuda X` | Razer Barracuda X | Wireless headset |
| `Razer Barracuda Pro` | Razer Barracuda Pro | Wireless headset (ANC) |
| `Razer Kishi` | Razer Kishi | Mobile game controller |
| `Razer Opus` | Razer Opus | ANC headphones |
| `Razer Hammerhead` | Razer Hammerhead TWS | True wireless earbuds |

## Sample Advertisements

```
Razer Leviathan V3:
  Service UUID: fd65
  Local name: Razer Lev3
  Manufacturer data: 8e06 a3b7c4e8f21d6a90

Razer Barracuda:
  Service UUID: fd65
  Local name: Razer Barracuda
  Manufacturer data: 8e06 f8d2a1b6c94e7320

Razer Kishi:
  Service UUID: fd65
  Local name: Razer Kishi
  Manufacturer data: 8e06 c7e5f3a2d8b14960
```

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

Razer devices typically use a static BLE MAC address, making this a stable identifier.

## Detection Significance

- Indicates presence of gaming peripherals
- Product name reveals device category (speaker, headset, controller)
- BLE used for app configuration and firmware updates
- Some Razer products support both BLE audio and proprietary 2.4GHz wireless

## Parsing Strategy

1. Match on service_uuid `fd65` OR local_name matching `Razer *`
2. Extract product name from local_name (strip "Razer " prefix)
3. Categorize by product type if possible (speaker, headset, controller)
4. Return device class `gaming_peripheral`

## References

- [Razer](https://www.razer.com/) -- manufacturer website
- [Bluetooth SIG UUID Database](https://www.bluetooth.com/specifications/assigned-numbers/) -- UUID `0xFD65` assigned to Razer Inc.
