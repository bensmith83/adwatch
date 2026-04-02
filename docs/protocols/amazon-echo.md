# Amazon Echo / Alexa BLE Protocol

## Overview

Amazon Echo and Alexa-enabled devices broadcast BLE advertisements for setup, companion app connectivity, and device discovery. Echo devices use service UUID `0xFE00` and are identified by their local name starting with "Echo".

**Important:** UUID `0xFE00` is shared with Amazon Fire TV devices. The parser must disambiguate by local name -- Echo devices advertise with names like "Echo Pop-35U" or "Echo Dot-XXX", while Fire TV devices use "AFTMM" patterns or have no local name.

## Identifiers

- **Service UUID:** `0xFE00` (16-bit)
- **Local name pattern:** `Echo *` (e.g. "Echo Pop-35U", "Echo Dot-XXX", "Echo Show-XXX")
- **Company ID:** Not present in advertisement
- **Device class:** `smart_speaker`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFE00` | Shared with Amazon Fire TV |
| Local name | `Echo *` | Model and short ID suffix |

### Disambiguating from Amazon Fire TV

Both Echo and Fire TV devices use service UUID `0xFE00`. To distinguish:

| Feature | Echo | Fire TV |
|---------|------|---------|
| Local name | `Echo Pop-XXX`, `Echo Dot-XXX`, etc. | `AFTMM*` pattern or absent |
| Device class | `smart_speaker` | `streaming_device` |
| Form factor | Speaker / display | Streaming stick / box |

**Rule:** If local_name starts with `Echo `, treat as Amazon Echo. Otherwise, fall through to the Fire TV parser.

### Service Data Format (on UUID `0xFE00`)

22 bytes observed:

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0 | 1 | Protocol marker | `0x01` observed |
| 1-4 | 4 | Device ID | Unique per device |
| 5-21 | 17 | Payload | Device state, capabilities |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid + local_name | Echo device nearby |
| Device model | local_name | Pop, Dot, Show, Studio, etc. |
| Short device ID | local_name suffix | e.g. "35U" from "Echo Pop-35U" |

### What We Cannot Parse (requires GATT)

- Alexa account association
- WiFi configuration status
- Firmware version
- Current playback state
- Volume level
- Smart home device list

## Local Name Pattern

Echo devices advertise with the product line followed by a short alphanumeric suffix:

```
Echo {model}-{suffix}
```

Examples: `Echo Pop-35U`, `Echo Dot-4KM`, `Echo Show-8R2`, `Echo Studio-A1B`

## Known Models

| Name Pattern | Product | Notes |
|-------------|---------|-------|
| `Echo Pop-*` | Echo Pop | Compact smart speaker |
| `Echo Dot-*` | Echo Dot | Small spherical speaker |
| `Echo Show-*` | Echo Show | Smart display with screen |
| `Echo Studio-*` | Echo Studio | High-fidelity smart speaker |
| `Echo -* ` | Echo (standard) | Mid-range smart speaker |

## Sample Advertisements

```
Echo Pop:
  Service UUID: fe00
  Local name: Echo Pop-35U
  Service data (fe00): 01a3b7c4e8f21d6a9053b8e4c7f2a1d50e42a1b6

Echo Dot:
  Service UUID: fe00
  Local name: Echo Dot-4KM
  Service data (fe00): 01f8d2a1b6c94e7320a1d8f3b5e6c0a47252c3d8

Echo Show:
  Service UUID: fe00
  Local name: Echo Show-8R2
  Service data (fe00): 01c7e5f3a2d8b14960f2c8a7e3d1b59a4163e4f9
```

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

Echo devices typically use a static or semi-static BLE MAC address.

## Detection Significance

- Indicates Amazon smart home ecosystem presence
- Model name reveals device type (speaker vs. display)
- Always-on BLE for Alexa app connectivity and setup
- High prevalence in residential environments

## Parsing Strategy

1. Match on local_name starting with `Echo `
2. Extract model name from local_name (word after "Echo", before "-")
3. Extract short device ID from suffix (after last "-")
4. Return device class `smart_speaker`
5. Must coexist with amazon_fire_tv parser -- only claim ads with `Echo` local name

## References

- [Amazon Echo Product Line](https://www.amazon.com/echo) -- manufacturer product pages
- Bluetooth SIG UUID Database -- UUID `0xFE00`
