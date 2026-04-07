# EPOS Audio BLE Protocol

## Overview

EPOS (formerly Sennheiser Communications) conference speakerphones and headsets advertise via BLE using company ID 0x0082 and a custom 128-bit service UUID. These devices are used in enterprise conference rooms and home offices.

## Identifiers

- **Company ID:** `0x0082` (Sennheiser Communications A/S / EPOS)
- **Service UUID:** `63331358-23C1-11E5-B696-FEFF819CDC9F` (custom EPOS service)
- **Local name pattern:** `EPOS {model}` (e.g., `EPOS EXPAND 40`)
- **Device class:** `audio`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0082` | Sennheiser/EPOS registered |
| Service UUID | `63331358-...` | Custom EPOS app communication service |
| Local name | `EPOS {model}` | Model name in advertisement |

### Manufacturer Data Structure

Total: 8 bytes (2 company ID + 6 payload)

#### Examples

```
82 00 60 bf 74 94 16 00
82 00 e0 c0 74 94 16 00
82 00 74 bd 74 94 16 00
82 00 53 bf 74 94 16 00
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0-1 | 2 | `82 00` | Company ID 0x0082 (little-endian) |
| 2 | 1 | varies | Status/state byte (varies between ads) |
| 3 | 1 | varies | Status/state byte (varies between ads) |
| 4-5 | 2 | `74 94` | Device identifier (consistent across ads for same device) |
| 6-7 | 2 | `16 00` | Protocol/firmware version |

Bytes 2-3 change between advertisements from the same device, suggesting they encode connection state or status. Bytes 4-5 remain constant for the same physical device, acting as a device identifier.

### Known Models

| Local Name | Product |
|------------|---------|
| `EPOS EXPAND 40` | Conference speakerphone (USB-C + Bluetooth) |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | company_id, service_uuid | EPOS device nearby |
| Model name | local_name | Product identification |
| Device ID | mfr_data bytes 4-5 | Consistent per-device |
| Protocol version | mfr_data bytes 6-7 | Firmware/protocol indicator |
| State bytes | mfr_data bytes 2-3 | Connection/device state |

### What We Cannot Parse (requires GATT connection or EPOS Connect app)

- Battery level
- Audio routing state
- Firmware version details
- Call status
- Volume level

## Identity Hashing

```
identifier = SHA256("epos:{mac}")[:16]
```

## Detection Significance

- Indicates enterprise/conference room environment
- EPOS EXPAND 40 is a premium conference speakerphone
- Multiple EPOS devices suggest a corporate office setting

## References

- [EPOS](https://www.eposaudio.com/) — manufacturer website
- Company ID 0x0082 registered to Sennheiser Communications A/S (now EPOS)
