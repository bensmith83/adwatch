# DREO Fan/Appliance BLE Protocol

## Overview

DREO smart fans and air circulators advertise via BLE with custom service UUID 5348 and company ID 0x4648 ("HF" in ASCII). The local name follows the pattern `DREO{model_id}` where the suffix encodes product model information.

## Identifiers

- **Service UUID:** `5348` (custom — "SH" in ASCII)
- **Company ID:** `0x4648` ("HF" in ASCII)
- **Local name pattern:** `DREO{model_id}` (e.g., `DREOac03lD9`, `DREOcd05wA8`)
- **Device class:** `fan`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `5348` | Custom UUID |
| Company ID | `0x4648` | "HF" in ASCII — likely internal identifier |
| Local name | `DREO{model}` | Model suffix varies by product |

### Manufacturer Data Structure

Total: 5 bytes (2 company ID + 3 payload)

#### Example

```
48 46 01 00 03
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0–1 | 2 | `48 46` | Company ID 0x4648 (little-endian) |
| 2 | 1 | `01` | Unknown — possibly protocol version |
| 3 | 1 | `00` | Unknown — possibly device state |
| 4 | 1 | `03` | Unknown — possibly device type |

The manufacturer data payload is identical across observed devices, suggesting it encodes firmware/protocol version rather than device-specific information.

### Local Name Model IDs

| Local Name | Model ID | Likely Product |
|------------|----------|----------------|
| `DREOac03lD9` | `ac03lD9` | DREO tower fan |
| `DREOcd05wA8` | `cd05wA8` | DREO air circulator |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid, company_id, or local_name | DREO device nearby |
| Model identifier | local_name suffix | Product-specific code |

### What We Cannot Parse (requires GATT connection or app)

- Fan speed
- Oscillation mode
- Timer settings
- Temperature reading (for models with sensors)
- Power state

## Identity Hashing

```
identifier = SHA256("dreo:{mac}")[:16]
```

## Detection Significance

- Indicates a DREO fan or air circulator
- Always-on BLE advertisement when powered
- Common consumer home appliance

## References

- [DREO](https://www.dreo.com/) — manufacturer website
- Service UUID `5348` and company ID `0x4648` are internal DREO identifiers
