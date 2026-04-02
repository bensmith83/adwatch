# Danalock Smart Lock BLE Protocol

## Overview

Danalock smart locks broadcast BLE advertisements for discovery and pairing with the Danalock companion app. The advertisement primarily serves as a presence beacon -- lock/unlock operations and status queries require a GATT connection with authentication.

## Identifiers

- **Service UUID:** `0xFD92` (16-bit, assigned to Danalock ApS)
- **Local name pattern:** `DL-XXXXXXXXXX` (`DL-` prefix followed by numeric device ID)
- **Device class:** `smart_lock`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFD92` | Danalock ApS assigned UUID |
| Local name | `DL-XXXXXXXXXX` | `DL-` prefix with numeric ID |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid or local_name | Danalock nearby |
| Device name | local_name | Full advertised name |
| Device ID | local_name suffix | Numeric ID after `DL-` prefix |

### What We Cannot Parse (requires GATT / not documented)

- Lock state (locked / unlocked / jammed)
- Battery level
- Firmware version
- Hardware model (V3, V4, etc.)
- Access log / user history
- Service data contents (format not publicly documented)

## Local Name Pattern

Danalock devices advertise with a `DL-` prefix followed by a numeric identifier:

```
DL-{device_id}
```

Examples: `DL-1234567890`, `DL-0042851963`, `DL-9876543210`

The numeric ID uniquely identifies the lock unit and is printed on the device label.

## Sample Advertisements

```
Danalock V3:
  Service UUID: fd92
  Local name: DL-1234567890

Danalock V4:
  Service UUID: fd92
  Local name: DL-0042851963
```

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

Danalock devices use a static BLE MAC address, making this a stable identifier.

## Detection Significance

- Indicates presence of a smart lock -- security-sensitive device
- Always-on BLE advertisement for app connectivity
- The device ID in the local name is static and unique per lock
- Presence reveals a smart-lock-equipped entry point

## Parsing Strategy

1. Match on service_uuid `fd92` OR local_name matching `DL-*`
2. Extract device ID from local_name (strip `DL-` prefix)
3. Return device class `smart_lock`

## References

- [Danalock](https://danalock.com/) -- manufacturer website
- [Bluetooth SIG UUID Database](https://www.bluetooth.com/specifications/assigned-numbers/) -- UUID `0xFD92` assigned to Danalock ApS
