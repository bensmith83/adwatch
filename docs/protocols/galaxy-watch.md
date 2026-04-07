# Samsung Galaxy Watch BLE Protocol

## Overview

Samsung Galaxy Watch devices advertise via BLE with service UUID FD69 (Bluetooth SIG assigned to Samsung Electronics). The service data payload contains device identification and state information. When discoverable, the local name includes the model (e.g., "Galaxy Watch Active2(6105) LE").

## Identifiers

- **Service UUID:** `FD69` (16-bit, Bluetooth SIG assigned to Samsung Electronics)
- **Local name pattern:** `Galaxy Watch {model}({serial}) LE`
- **Device class:** `wearable`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `FD69` | Bluetooth SIG assigned to Samsung |
| Local name | `Galaxy Watch ...` | Present when discoverable |

### Service Data Structure

Variable length (14–20 bytes). Three formats observed:

#### Short Format (14 bytes)

```
03 58 e4 27 ee db 3e 59 ae 89 b6 32 ec 01
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0 | 1 | `03` | Unknown — possibly message type |
| 1–12 | 12 | `58 e4...32 ec` | Device identifier / encrypted payload |
| 13 | 1 | `01` | Unknown — possibly state flag |

#### Long Format (20 bytes)

```
10 58 e4 27 ee db 3e 59 ae 89 b6 32 ec 52 00 1e 1a 20 ec 8b
```

Extended payload, first byte `10` instead of `03`. May contain additional device state.

#### Named Format (15 bytes)

```
00 9a f2 44 5b 83 4b 4c 9a c7 20 7c 82 40 00
```

Seen when local name is present. First byte `00` may indicate discoverable mode.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid or local_name | Galaxy Watch nearby |
| Model name | local_name | When discoverable |
| Payload type | service_data[0] | 0x00, 0x03, 0x10 observed |

### What We Cannot Parse (requires GATT connection or Galaxy Wearable app)

- Watch face / current activity
- Heart rate / health data
- Battery level
- Notification state
- Firmware version

## Identity Hashing

```
identifier = SHA256("galaxy_watch:{mac}")[:16]
```

## Detection Significance

- Indicates a Samsung Galaxy Watch wearable nearby
- Uses rotating random addresses for privacy
- Multiple advertisement formats based on connection state

## References

- Bluetooth SIG 16-bit UUID assignment: FD69 = Samsung Electronics Co., Ltd.
- [Samsung Galaxy Watch](https://www.samsung.com/global/galaxy/galaxy-watch/) — product page
