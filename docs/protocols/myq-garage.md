# Chamberlain / LiftMaster MyQ Garage Door Opener

## Overview

Chamberlain and LiftMaster MyQ garage door openers broadcast BLE advertisements for proximity-based control via the MyQ app. BLE enables local device discovery and short-range door open/close commands. Actual door control requires an authenticated GATT connection — the advertisement alone does not expose door state.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `MyQ-XXX` pattern | e.g. `MyQ-75D`, suffix is a device identifier |
| Manufacturer data prefix | `78082b00` | Company ID `0x0878` (Chamberlain Group) |

No known service UUID is advertised. The local name pattern is the primary identification signal.

### Manufacturer Data

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0-1 | 2 bytes | Company ID | `0x0878` — Chamberlain Group (little-endian: `7808`) |
| 2-3 | 2 bytes | Flags / protocol version | `0x002B` — purpose unknown |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | local_name | MyQ garage door opener nearby |
| Device ID | local_name suffix | e.g. `75D` from `MyQ-75D` |
| Manufacturer | company_id `0x0878` | Chamberlain Group |

### What We Cannot Parse (requires GATT)

- Door state (open / closed / opening / closing)
- Firmware version
- Device model (wall mount, belt drive, etc.)
- Battery level (for battery backup models)
- Light status

## Local Name Pattern

```
MyQ-{device_id}
```

Examples: `MyQ-75D`, `MyQ-A3F`, `MyQ-012`

The suffix is a short hex-like device identifier, typically 3 characters.

## Device Class

```
garage_door
```

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

## Detection Significance

- Garage door opener — reveals the presence and proximity of a garage entry point
- Security consideration: detecting garage door openers in BLE range identifies controllable physical access points
- BLE range is limited, so detection implies close proximity to the garage
- MyQ devices broadcast continuously for app-based convenience features

## References

- [MyQ App](https://www.myq.com/) — Chamberlain Group smart garage platform
- [Chamberlain Group](https://www.chamberlaingroup.com/) — manufacturer (also LiftMaster, Craftsman)
