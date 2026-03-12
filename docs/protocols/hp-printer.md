# HP Printers

## Overview

HP printers broadcast BLE advertisements for discovery and setup via the HP Smart app. They can be identified by company ID `0x0434` (HP Inc.) in manufacturer data, service UUIDs `0xFDF7`, `0xFE77`, and `0xFE78`, and by their local name which typically contains the printer model.

## BLE Advertisement Format

### Identification

Multiple signals, any of which identifies an HP printer:

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0434` | HP Inc. manufacturer data |
| Service UUID | `0xFDF7` | HP printer service |
| Service UUID | `0xFE77` | Hewlett-Packard Company (BLE SIG assigned) |
| Service UUID | `0xFE78` | Hewlett-Packard Company (BLE SIG assigned) |
| Local name | Model string | e.g. `M479fdw Color LJ`, `HP ENVY 6000` |

### Manufacturer Data

HP printers broadcast manufacturer-specific data with company ID `0x0434`. The payload structure is proprietary. Observed payloads vary in length.

### Service Data

Service UUIDs `0xFE77` and `0xFE78` are both assigned to Hewlett-Packard Company in the Bluetooth SIG registry. Their service data payloads are proprietary.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | company_id or service_uuid | HP printer is nearby |
| Printer model | local_name | Human-readable model string |
| Manufacturer data | company_id `0x0434` payload | Proprietary, not decoded |

### What We Cannot Parse (requires GATT)

- Printer IP address (IPv4, IPv6)
- Printer MAC address
- Print queue status
- Ink/toner levels

## Identity Hashing

```
identifier = SHA256("{mac}:{manufacturer_data_hex}")[:16]
```

HP printers typically use a static public BLE MAC address, making identification straightforward.

## Known Models Observed

| Local Name | Model |
|-----------|-------|
| `M479fdw Color LJ` | HP Color LaserJet Pro MFP M479fdw |

## Detection Significance

- Infrastructure device — indicates an office or home office environment
- HP printers broadcast continuously when BLE is enabled
- Multiple service UUIDs make detection reliable even if one signal is missed

## Future Work

- Reverse-engineer manufacturer_data payload to extract model info without relying on local_name
- Determine if service data on `0xFE77`/`0xFE78` contains useful metadata
- Catalog advertisement differences across HP printer product lines (LaserJet, OfficeJet, ENVY, etc.)

## References

- [Bluetooth SIG — Service UUID 0xFDF7](https://www.bluetooth.com/specifications/assigned-numbers/) (assigned to HP Inc.)
- [Bluetooth SIG — Service UUID 0xFE77, 0xFE78](https://www.bluetooth.com/specifications/assigned-numbers/) (assigned to Hewlett-Packard Company)
- [Bluetooth SIG — Company ID 0x0434](https://www.bluetooth.com/specifications/assigned-numbers/) (HP Inc.)
