# iHealth BLE Smart Health Device Protocol

## Overview

iHealth Labs makes BLE-connected health monitors (blood pressure, glucose, SpO2, scales). Their devices advertise with the Bluetooth SIG assigned service UUID FE4A and company ID 0x020E. Local names follow the pattern `BLESmart_XXXX` where XXXX is a hex-encoded device identifier.

## Identifiers

- **Service UUID:** `FE4A` (16-bit, Bluetooth SIG assigned to iHealth Labs)
- **Company ID:** `0x020E` (iHealth Labs Inc.)
- **Local name pattern:** `BLESmart_XXXXXXXXXXXXXXXXXXXXXXXX` (hex device ID, typically 20+ chars)
- **Device class:** `health_monitor`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `FE4A` | Bluetooth SIG assigned to iHealth Labs |
| Company ID | `0x020E` | iHealth Labs Inc. |
| Local name | `BLESmart_XXXX...` | Hex-encoded device identifier |

### Manufacturer Data Structure

Total: 7 bytes (2 company ID + 5 payload)

#### Example

```
0e 02 01 00 02 00 02
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0–1 | 2 | `0e 02` | Company ID 0x020E (little-endian) |
| 2 | 1 | `01` | Unknown — possibly protocol version |
| 3 | 1 | `00` | Unknown — possibly device type |
| 4 | 1 | `02` | Unknown — possibly status flags |
| 5 | 1 | `00` | Unknown |
| 6 | 1 | `02` | Unknown — possibly mode indicator |

### Local Name Format

The `BLESmart_` prefix is followed by a hex string that serves as a unique device identifier. The length varies but is typically 20–24 hex characters. Example: `BLESmart_000000BAEA9D7A5D9F79`.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid or local_name | iHealth device nearby |
| Device ID | local_name suffix | Hex identifier unique to device |
| Device type hint | manufacturer_data payload | Needs further analysis |

### What We Cannot Parse (requires GATT connection)

- Health readings (blood pressure, glucose, SpO2, weight)
- Device model identification
- Battery level
- User profile/settings
- Historical measurements

## Identity Hashing

```
identifier = SHA256("ihealth:{mac}")[:16]
```

## Detection Significance

- Indicates an iHealth health monitoring device
- Common consumer health devices (blood pressure cuffs, glucose meters, pulse oximeters, scales)
- BLE advertisement active when device is powered on and discoverable

## References

- Bluetooth SIG 16-bit UUID assignment: FE4A = iHealth Labs Inc.
- [iHealth](https://ihealthlabs.com/) — manufacturer website
