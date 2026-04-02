# in-lite Outdoor Landscape Lighting

## Overview

in-lite outdoor landscape lighting systems broadcast BLE advertisements for control via the in-lite app. These are professional-grade outdoor LED lighting fixtures used for garden, pathway, and architectural lighting. BLE is used for local control including dimming, color adjustment, and scheduling.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `inlitebt` | Exact or prefix match |
| Service UUID (advertised) | `fef1` | 16-bit, assigned to CSR plc, used by in-lite for BLE control |

The `FEF1` service UUID is assigned to CSR plc (now Qualcomm) in the Bluetooth SIG registry but is used by in-lite for their lighting control protocol. The local name `inlitebt` is the primary identification signal.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | local_name or service_uuids | in-lite lighting controller nearby |

### What We Cannot Parse (requires GATT)

- Light on/off state
- Brightness level
- Color temperature or RGB values
- Scheduling configuration
- Zone/group assignment
- Firmware version
- Number of connected fixtures

## Device Class

```
lighting
```

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

## Detection Significance

- Outdoor landscape lighting — indicates residential or commercial property with professional-grade outdoor lighting
- BLE control range is limited, so detection implies proximity to the lighting controller
- Devices broadcast continuously for app-based convenience control
- in-lite systems are 12V low-voltage, typically installed by landscape professionals

## References

- [in-lite Outdoor Lighting](https://www.in-lite.com/) — manufacturer website
- [Bluetooth SIG UUID Database](https://www.bluetooth.com/specifications/assigned-numbers/) — `FEF1` assigned to CSR plc
