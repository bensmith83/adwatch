# Fitbit (Fitness Trackers)

## Overview

Fitbit devices broadcast BLE advertisements for discovery and pairing. The advertisements use Qualcomm's company ID and contain device identification data. Fitbit was acquired by Google in 2021; newer devices may use different protocols.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x000A` | Qualcomm (Fitbit uses Qualcomm BLE chipsets) |
| Local name | `Fitbit*` or model-specific | e.g. `Charge 5`, `Versa 3` |

### Manufacturer Data Layout

Based on reverse engineering (pewpewthespells.com):

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| 0 | 1 | Airlink opcode | Message type identifier |
| 1 | 1 | Device type | Identifies tracker model |
| 2+ | var | Payload | Opcode-dependent data |

### Known Airlink Opcodes

| Opcode | Name | Notes |
|--------|------|-------|
| `0x01` | Advertisement | Standard broadcast |
| `0x02` | Pairing request | During setup |
| `0x06` | Status | Device state broadcast |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Fitbit present | company_id match | Fitbit device nearby |
| Device type | byte 1 | Model identifier |
| Airlink state | opcode | Pairing/advertising/status |

### What We Cannot Parse from Advertisements

- Step count, heart rate, sleep data
- Battery level
- User information
- Detailed device model/firmware

All health and fitness data requires authenticated Bluetooth connection to Fitbit's proprietary protocol.

## Detection Significance

- Very common consumer wearable
- Broadcasts continuously when not connected to phone
- Privacy indicator — reveals user has a Fitbit nearby
- Company ID `0x000A` is Qualcomm, so must check payload structure to distinguish from other Qualcomm devices

## References

- **RE writeup**: https://pewpewthespells.com/blog/fitbit_re.html
- **Theengs decoder**: https://decoder.theengs.io/devices/devices.html
