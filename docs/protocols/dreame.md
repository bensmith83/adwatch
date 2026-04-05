# Dreame Robot Vacuum BLE Protocol

## Overview

Dreame is a Chinese manufacturer of robot vacuums and cleaning appliances. Their devices advertise via BLE using the assigned service UUID FD92 and local names matching `DL-XXXXXXXXXX` where the suffix is a serial number.

## Identifiers

- **Service UUID:** `FD92` (16-bit, Bluetooth SIG assigned to Dreame)
- **Local name pattern:** `DL-XXXXXXXXXX` (e.g., `DL-1102102677`)
- **Device class:** `vacuum`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `FD92` (full: `0000fd92-0000-1000-8000-00805f9b34fb`) | Bluetooth SIG assigned to Dreame |
| Local name | `DL-XXXXXXXXXX` | DL = Dreame Lidar(?), suffix = serial number |

### Local Name Structure

```
DL-{serial_number}
```

The `DL` prefix likely stands for "Dreame Lidar" (LiDAR-equipped models). The serial number is a 10-digit numeric string.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid or local_name | Dreame vacuum nearby |
| Serial number | local_name suffix | 10-digit numeric serial |
| Device name | local_name | Full advertised name |

### What We Cannot Parse (requires GATT connection)

- Battery level
- Cleaning status (cleaning, charging, idle)
- Map data
- Error/fault codes
- Firmware version
- Wi-Fi configuration

## Sample Advertisements

```
DL-1102102677:
  Service UUID: FD92
  Local name: DL-1102102677
  Manufacturer data: (none)
  Sightings: 204
```

No manufacturer data or service data was observed — the device relies on UUID and local name for identification.

## Identity Hashing

```
identifier = SHA256("dreame:{mac}")[:16]
```

## Detection Significance

- Indicates a Dreame robot vacuum in the area
- Always-on BLE for app connectivity and control
- Common in smart home environments

## Parsing Strategy

1. Match on service UUID `FD92` OR local_name matching `^DL-`
2. Extract serial number from local_name suffix
3. Return device class `vacuum`

## References

- [Dreame](https://www.dreametech.com/) — manufacturer website
- Bluetooth SIG 16-bit UUID assignment: FD92 = Shenzhen Dreame Technology Co., Ltd.
