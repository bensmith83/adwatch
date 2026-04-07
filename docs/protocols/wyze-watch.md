# Wyze Watch BLE Protocol

## Overview

Wyze Watch is an affordable smartwatch built on rebranded Xiaomi/Huami hardware. It advertises via BLE using company ID 0x0649 and the Xiaomi MiBeacon protocol (service UUID FE95). The BLE MAC address is embedded in both the manufacturer data and the MiBeacon service data.

## Identifiers

- **Company ID:** `0x0649` (Xiaomi/Huami ODM chain)
- **Service UUIDs:** `FE95` (Xiaomi MiBeacon), `B167`, `FEE7` (Tencent WeChat BLE)
- **Local name pattern:** `Wyze Watch {size}` (e.g., `Wyze Watch 47`)
- **Device class:** `wearable`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0649` | Xiaomi/Huami |
| Service UUID | `FE95` | Xiaomi MiBeacon protocol |
| Service UUID | `FEE7` | Tencent WeChat mini-program BLE |
| Service UUID | `B167` | Custom Wyze/Huami service |
| Local name | `Wyze Watch {size}` | Watch size in mm |

### Manufacturer Data Structure

Total: 12 bytes (2 company ID + 10 payload)

#### Example

```
49 06 02 09 00 00 2c aa 8e d2 62 82
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0-1 | 2 | `49 06` | Company ID 0x0649 (little-endian) |
| 2-3 | 2 | `02 09` | Device type/model identifier |
| 4-5 | 2 | `00 00` | Reserved/padding |
| 6-11 | 6 | `2c aa 8e d2 62 82` | BLE MAC address |

### MiBeacon Service Data (FE95)

```
31 20 8f 03 00 2c aa 8e d2 62 82 09
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0-1 | 2 | `31 20` | Frame control (capabilities/encryption flags) |
| 2-3 | 2 | `8f 03` | Device type (0x038F LE = Wyze Watch variant) |
| 4 | 1 | `00` | Frame counter |
| 5-10 | 6 | `2c aa 8e d2 62 82` | MAC address |
| 11 | 1 | `09` | Capability/pairing flags |

### Known Variants

| Local Name | Size | Notes |
|------------|------|-------|
| `Wyze Watch 47` | 47mm | Larger variant |
| `Wyze Watch 44` | 44mm | Standard variant |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | company_id, FE95 | Wyze Watch nearby |
| Watch size | local_name | 44mm or 47mm |
| MAC address | mfr_data bytes 6-11 | BLE MAC embedded in payload |
| Device type | mfr_data bytes 2-3 | Model/hardware identifier |
| MiBeacon type | FE95 data bytes 2-3 | Xiaomi device type code |

### What We Cannot Parse (requires GATT connection or Wyze app)

- Heart rate
- Step count
- Sleep data
- Battery level
- Notification state

## Identity Hashing

```
identifier = SHA256("wyze_watch:{mac}")[:16]
```

## Detection Significance

- Indicates a Wyze ecosystem user
- Built on Xiaomi hardware — also triggers MiBeacon detection
- Budget smartwatch common in consumer environments

## References

- [Wyze Watch](https://www.wyze.com/products/wyze-watch) — product page
- FE95 = Xiaomi MiBeacon protocol (Bluetooth SIG assigned)
- FEE7 = Tencent Holdings WeChat BLE service
