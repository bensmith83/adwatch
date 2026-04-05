# Sphero Robot BLE Protocol

## Overview

Sphero makes programmable robotic balls and educational robots. The Sphero BOLT is their flagship STEAM education robot. Sphero devices advertise via BLE using a custom 128-bit service UUID and a local name pattern `SB-XXXX` where XXXX is a 4-character hex device identifier.

## Identifiers

- **Service UUID:** `00010001-574F-4F20-5370-6865726F2121` (128-bit, decodes to ASCII "WOO Sphero!!")
- **Local name pattern:** `SB-XXXX` (e.g., `SB-9B13`, `SB-A6B9`)
- **Device class:** `toy`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `00010001-574F-4F20-5370-6865726F2121` | Custom Sphero service |
| Local name | `SB-XXXX` | SB = Sphero BOLT, XXXX = hex device ID |

### UUID Structure

The Sphero service UUID embeds ASCII text:

```
00010001-574F-4F20-5370-6865726F2121
         W O   O     S p   h e r o ! !
```

Reading bytes 5-16 as ASCII: "WOO Sphero!!"

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid or local_name | Sphero robot nearby |
| Device ID | local_name suffix | 4-char hex identifier (last 4 of SB-XXXX) |
| Model | local_name prefix | SB = BOLT |

### What We Cannot Parse (requires GATT connection)

- Battery level
- Firmware version
- LED matrix state
- Sensor data (accelerometer, gyroscope, compass)
- Motor control / speed
- Programming state

## Sample Advertisements

From captured data, 8 unique Sphero BOLT devices were observed:

```
SB-9B13: sightings=66
SB-9DD2: sightings=78
SB-A6B9: sightings=90
SB-2C30: sightings=57
SB-238A: sightings=54
SB-B821: sightings=65
SB-8019: sightings=63
SB-BF86: sightings=54
```

All share the same service UUID and have no manufacturer data or service data — identification is purely by UUID and local name.

## Identity Hashing

```
identifier = SHA256("sphero:{mac}")[:16]
```

## Detection Significance

- Indicates Sphero educational/toy robots in the area
- Common in schools, makerspaces, and STEAM education settings
- 8 devices clustered together suggests a classroom environment
- BLE advertisement is always-on when the robot is powered

## Parsing Strategy

1. Match on service UUID `00010001-574F-4F20-5370-6865726F2121` OR local_name matching `^SB-[A-F0-9]{4}$`
2. Extract device ID from local_name suffix (4 hex chars after `SB-`)
3. Set model to "BOLT" for SB- prefix
4. Return device class `toy`

## References

- [Sphero](https://sphero.com/) — manufacturer website
- [Sphero BOLT](https://sphero.com/products/sphero-bolt) — product page
- [Sphero SDK](https://sdk.sphero.com/) — developer documentation
