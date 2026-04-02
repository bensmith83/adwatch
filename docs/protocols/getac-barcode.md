# Getac Rugged Barcode Scanner

## Overview

Getac BC22 rugged barcode scanners broadcast BLE advertisements for pairing with mobile devices and rugged tablets in enterprise and industrial environments. These are purpose-built scanners for warehouse logistics, field service, and asset tracking. The local name encodes the device serial number.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `BC22XXXXXXXXXXXXGetac` pattern | e.g. `BC220267720008Getac`, serial embedded in name |
| Service UUID (advertised) | `00000000-0000-1000-1b7f-430ea194e6cf` | 128-bit custom Getac service |
| Manufacturer data prefix | `0f00abd0540008` | Company ID `0x000F` (Texas Instruments) |

The TI company ID (`0x000F`) reflects the Bluetooth chipset used, not the device manufacturer. The custom 128-bit service UUID and the distinctive local name pattern are the primary identification signals.

### Manufacturer Data

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0-1 | 2 bytes | Company ID | `0x000F` — Texas Instruments (little-endian: `0f00`) |
| 2-6 | 5 bytes | Device data | `abd0540008` — likely hardware revision or configuration |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | local_name or service_uuids | Getac barcode scanner nearby |
| Serial number | local_name | Digits between `BC22` prefix and `Getac` suffix |
| Device model | local_name prefix | `BC22` identifies the product line |

### What We Cannot Parse (requires GATT)

- Scanned barcode data
- Battery level
- Firmware version
- Scanner configuration (symbology settings, scan mode)
- Paired host device

## Local Name Pattern

```
BC22{serial_number}Getac
```

Examples: `BC220267720008Getac`

The serial number portion is a numeric string embedded between the `BC22` model prefix and the `Getac` brand suffix.

## Device Class

```
barcode_scanner
```

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

The serial number in the local name provides a stable device identity even if the BLE MAC rotates.

## Detection Significance

- Enterprise/industrial device — indicates warehouse, logistics, or field service operations
- Presence of rugged barcode scanners suggests inventory management or asset tracking workflows
- These devices broadcast continuously when powered on and not connected to a host

## References

- [Getac BC22](https://www.getac.com/) — rugged barcode scanner product line
- [Bluetooth SIG Company Identifiers](https://www.bluetooth.com/specifications/assigned-numbers/) — Texas Instruments `0x000F`
