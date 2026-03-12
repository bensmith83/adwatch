# iBeacon

## Overview

iBeacon is Apple's standardized BLE beacon format. It uses the Apple company ID (`0x004C`) with a fixed subtype (`0x02`) and 21-byte payload containing a UUID, Major, Minor, and TX Power. iBeacons are typically infrastructure devices — retail beacons, indoor positioning anchors, museum guides, etc.

Unlike phone advertisements, iBeacons use **stable identifiers** (UUID + Major + Minor don't rotate).

## BLE Advertisement Format

### Identification

- **Company ID:** `0x004C` (Apple Inc.)
- **Subtype:** `0x02`
- **Length byte:** `0x15` (21 bytes)
- **Total manufacturer data:** 25 bytes

Detect by checking: `data[2] == 0x02 and data[3] == 0x15`

### Byte Layout (25 bytes)

```
Offset  Size  Field
------  ----  -----
0–1     2     Company ID (0x4C 0x00, little-endian)
2       1     Subtype (0x02 = iBeacon)
3       1     Length (0x15 = 21)
4–19    16    Proximity UUID
20–21   2     Major (big-endian)
22–23   2     Minor (big-endian)
24      1     TX Power (signed int8, dBm at 1 meter)
```

### Proximity UUID

16-byte identifier typically assigned per organization or deployment. Format as standard UUID: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`.

### Major & Minor

16-bit unsigned integers (big-endian). Used hierarchically:
- **Major:** typically identifies a location or building
- **Minor:** typically identifies a specific beacon within that location

### TX Power

Signed 8-bit integer representing calibrated signal strength at 1 meter distance. Used for distance estimation:

```
if tx_power > 127:
    tx_power -= 256  # convert to signed
```

## Identity Hashing

iBeacon identifiers are **stable** — they don't rotate like phone MACs. The hash is based on UUID + Major + Minor (not MAC):

```
identifier = SHA256("{uuid}:{major}:{minor}")[:16]
```

## Raw Packet Examples

```
# iBeacon: UUID=2f234454-cf6d-4a0f-adf2-f4911ba9ffa6, Major=1, Minor=42, TX=-59dBm
4c 00 02 15 2f 23 44 54 cf 6d 4a 0f ad f2 f4 91
│  │  │  │  └──────────────────────────────────────── Proximity UUID (16 bytes)
│  │  │  └───────────────────────────────────────────  length (0x15 = 21)
│  │  └──────────────────────────────────────────────  subtype (0x02 = iBeacon)
│  └─────────────────────────────────────────────────  company ID high
└────────────────────────────────────────────────────  company ID low (Apple)

1b a9 ff a6 00 01 00 2a c5
│           │     │     └── TX Power (0xC5 = -59 dBm)
│           │     └──────── Minor (0x002A = 42)
│           └────────────── Major (0x0001 = 1)
└────────────────────────── UUID continued
```

## Common Deployments

| Use Case | UUID Pattern |
|----------|-------------|
| Estimote beacons | `b9407f30-f5f8-466e-aff9-25556b57fe6d` |
| Kontakt.io | Various per customer |
| Retail/indoor nav | Organization-specific |
| Home automation | User-configured |

## References

- [Apple iBeacon specification](https://developer.apple.com/ibeacon/) (requires Apple Developer account)
- [Bluetooth SIG Assigned Numbers](https://www.bluetooth.com/specifications/assigned-numbers/)
