# Samsung SmartThings BLE Protocol

## Overview

Samsung SmartThings devices (hubs, sensors, plugs, etc.) advertise via BLE with service UUID 1122 and local names following a distinctive pattern: `S` + 16 hex characters + `C`. The hex string serves as a device identifier. These advertisements contain no manufacturer data or service data payload — identification is purely through UUID and name.

## Identifiers

- **Service UUID:** `1122` (custom, not Bluetooth SIG assigned)
- **Local name pattern:** `S{16_hex_chars}C` (e.g., `S98039bf21cd187e2C`)
- **Device class:** `smart_home`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `1122` | Custom SmartThings UUID |
| Local name | `S{hex}C` | 18-char string: S + 16 hex + C |

### Local Name Structure

```
S 98039bf21cd187e2 C
│ └─────────────┘ │
│   Device ID     │
│   (16 hex)      │
Prefix           Suffix
```

The 16 hex characters (8 bytes) appear to be a device-specific identifier, possibly derived from the device's MAC address or a registration token.

### Advertisement Contents

These advertisements are minimal:
- **No manufacturer data** — no company ID or payload
- **No service data** — UUID is advertised but with no associated data
- **Address type:** random (rotating)

### Observed Devices

| Local Name | Sightings | Notes |
|------------|-----------|-------|
| `S98039bf21cd187e2C` | 151 | |
| `S201b91dbacb104cdC` | 118 | |
| `S283da1b32aee14ddC` | 52 | |
| `Sed9ccb98a762300eC` | 47 | |
| `S284acba5f5432ecbC` | ~20 | |
| `S24df0a06b5defbc1C` | ~5 | |
| `Sdbecf73443176f55C` | ~2 | |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid or local_name | SmartThings device nearby |
| Device ID | local_name hex portion | 16-char hex identifier |

### What We Cannot Parse (requires GATT connection or SmartThings app)

- Device type (sensor, plug, hub, etc.)
- Sensor readings
- Device state
- Battery level
- Firmware version

## Identity Hashing

```
identifier = SHA256("smartthings:{mac}")[:16]
```

## Detection Significance

- Indicates Samsung SmartThings ecosystem devices
- Multiple devices often present in SmartThings-equipped homes
- Always-on BLE advertisement

## References

- [Samsung SmartThings](https://www.smartthings.com/) — smart home platform
- Service UUID 1122 is a custom assignment by Samsung for SmartThings BLE discovery
