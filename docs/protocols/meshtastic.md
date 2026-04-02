# Meshtastic BLE Protocol

## Overview

Meshtastic is an open-source LoRa mesh networking project. Meshtastic nodes broadcast BLE advertisements to allow configuration and message exchange via companion mobile apps. The BLE advertisement primarily serves as a presence beacon and connection point -- actual mesh communication happens over LoRa radio, not BLE.

## Identifiers

- **Service UUID:** `6ba1b218-15a8-461f-9fa8-5dcae273eafd` (128-bit, Meshtastic primary service)
- **Local name pattern:** `Meshtastic_XXXX` (hex suffix derived from node ID)
- **Device class:** `mesh_node`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `Meshtastic_XXXX` | 4-char hex suffix from node ID |
| Service UUID | `6ba1b218-15a8-461f-9fa8-5dcae273eafd` | Meshtastic primary service |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid or local_name | Meshtastic node nearby |
| Short node ID | local_name suffix | Last 4 hex chars of node number |
| Device name | local_name | Full advertised name |

### What We Cannot Parse (requires GATT connection)

- Full node number (32-bit)
- Firmware version
- Hardware model (T-Beam, Heltec, etc.)
- Channel configuration
- Mesh network name / PSK
- Position (GPS coordinates)
- Battery level
- Message history

## Local Name Pattern

Meshtastic devices advertise with a fixed prefix and a 4-character hex suffix derived from the node's unique ID:

```
Meshtastic_{node_id_suffix}
```

Examples: `Meshtastic_a1b2`, `Meshtastic_3f4e`, `Meshtastic_00c7`

The suffix is the last 4 hex characters of the device's node number, providing a short identifier for the node within the mesh.

## Sample Advertisements

```
Meshtastic_a1b2:
  Service UUID: 6ba1b218-15a8-461f-9fa8-5dcae273eafd
  Local name: Meshtastic_a1b2

Meshtastic_3f4e:
  Service UUID: 6ba1b218-15a8-461f-9fa8-5dcae273eafd
  Local name: Meshtastic_3f4e
```

## Identity Hashing

```
identifier = SHA256("{mac}:meshtastic")[:16]
```

Meshtastic devices typically use a static BLE MAC address, making this a stable identifier.

## Detection Significance

- Indicates presence of LoRa mesh networking equipment
- Common among outdoor enthusiasts, emergency preparedness, and off-grid communication
- BLE advertisement is always-on when the node is powered, for app connectivity
- The hex suffix can correlate a BLE sighting with a specific node on the mesh

## Parsing Strategy

1. Match on service_uuid `6ba1b218-15a8-461f-9fa8-5dcae273eafd` OR local_name matching `Meshtastic_*`
2. Extract short node ID from local_name suffix (last 4 characters after `_`)
3. Return device class `mesh_node`

## References

- [Meshtastic](https://meshtastic.org/) -- project website
- [Meshtastic Firmware Documentation](https://meshtastic.org/docs/developers/firmware/portnum) -- port numbers and protocol details
- [Meshtastic GitHub](https://github.com/meshtastic) -- source code and BLE service definitions
- Bluetooth SIG UUID database
