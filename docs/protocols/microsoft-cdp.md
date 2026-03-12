# Microsoft CDP (Connected Devices Platform)

## Overview

Microsoft devices broadcast BLE advertisements using Company ID `0x0006` as part of the Connected Devices Platform (CDP). The payload encodes a scenario type and device type, enabling classification of Windows PCs, Xbox consoles, Surface devices, and even non-Microsoft devices that participate in CDP.

CDP is primarily a **classification** protocol for adwatch — we extract the device type but don't do deep identity parsing.

## BLE Advertisement Format

### Identification

- **AD Type:** `0xFF` (Manufacturer Specific Data)
- **Company ID:** `0x0006` (Microsoft, little-endian: `06 00`)

### Byte Layout

```
Offset  Size  Field
------  ----  -----
0–1     2     Company ID (0x06 0x00, little-endian)
2       1     Scenario Type
3       1     Version (upper 3 bits) + Device Type (lower 5 bits)
4+      var   Scenario-specific data
```

### Scenario Type (byte 2)

| Value | Scenario |
|-------|----------|
| `0x01` | Bluetooth connectivity |
| `0x06` | Cloud messaging |

Scenario `0x01` is the most commonly observed.

### Device Type (byte 3, lower 5 bits)

```
device_type = byte[3] & 0x1F
```

| Code | Device Type | Category |
|------|------------|----------|
| 1 | Xbox | entertainment |
| 6 | iPhone | phone |
| 7 | iPad | phone |
| 8 | Android | phone |
| 9 | Desktop (Windows) | computer |
| 11 | Windows Phone | phone |
| 12 | Linux | computer |
| 13 | Windows IoT | computer |
| 14 | Surface Hub | computer |
| 15 | Laptop (Windows) | computer |
| 16 | Tablet (Windows) | computer |

### Version (byte 3, upper 3 bits)

```
version = (byte[3] >> 5) & 0x07
```

CDP protocol version. Typically `0x01` or `0x02` in the wild.

## Classification Output

adwatch classifies Microsoft CDP advertisements as:
- `ad_type`: `microsoft_cdp_{device_name}` (e.g., `microsoft_cdp_laptop`, `microsoft_cdp_xbox`)
- `ad_category`: varies by device type (see table above)
- Falls back to `microsoft_cdp` / `computer` if device type is unknown

## Identity Hashing

```
identifier = SHA256("{mac}:{payload_hex}")[:16]
```

## Raw Packet Examples

```
# Windows laptop
06 00 01 2f ...
│  │  │  └──── version=1 (001), device_type=15 (01111) = laptop
│  │  └─────── scenario_type (0x01 = Bluetooth)
│  └────────── company ID high
└───────────── company ID low (Microsoft)

# Xbox console
06 00 01 21 ...
            └── version=1 (001), device_type=1 (00001) = Xbox

# Android device (via Microsoft apps)
06 00 01 28 ...
            └── version=1 (001), device_type=8 (01000) = Android
```

## Notes

- iPhones and iPads appear in CDP when Microsoft apps (Outlook, Edge, Teams) are installed and linked
- Android devices appear similarly when Microsoft services are active
- Xbox consoles broadcast CDP when Bluetooth is enabled
- Surface Hub uses a dedicated device type code
- Windows PCs broadcast more consistently than mobile devices

## References

- [Microsoft CDP Protocol (reverse-engineered)](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-cdp/)
- [Microsoft Swift Pair Documentation](https://learn.microsoft.com/en-us/windows-hardware/design/component-guidelines/bluetooth-swift-pair)
