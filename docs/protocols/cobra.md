# Cobra Electronics Plugin

## Overview

**Cobra Electronics** (Chicago) ships consumer vehicle accessories — radar/laser detectors and dash cams — that pair with the **Drive Smarter** mobile app (formerly **iRadar**) over BLE. Cobra has not been assigned a Bluetooth SIG company ID and does not emit manufacturer data; instead, the BLE fingerprint is a pair of proprietary 128-bit service UUIDs combined with the marketing model name in the GAP local-name field.

Two product families share the same primary UUID:

| Family | Model names | Device class |
|---|---|---|
| **RAD** radar / laser detectors | `RAD 480i`, `RAD 490i`, `RAD 700i`, `RAD 380`, … | `radar_detector` |
| **SC** dash cams | `SC 200`, `SC 201`, `SC 220`, `SC 220C` | `dashcam` |

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Primary service UUID | `2A668FA4-2902-4468-8568-3EBE69A930A0` (always) |
| Companion service UUID | `C46B558B-8DBB-46A8-A991-D0B6EA0DDD60` (SC dash cams only) |
| Manufacturer data | absent (no SIG CID assigned) |
| Local name | marketing model — e.g. `"RAD 480i"`, `"SC 220"` |

We require at least one of the Cobra UUIDs to be present. The local-name patterns `RAD <number>` and `SC <number>` are too generic to match on alone — without the UUID, an unrelated device named `RAD Beacon` would over-match.

### Device-Class Heuristic

If the local name matches `^RAD\s[0-9]{3,4}[A-Za-z]?$` we surface `device_class = radar_detector`. If it matches `^SC\s[0-9]{3,4}[A-Za-z]?$` we surface `device_class = dashcam`. Otherwise we fall back to `vehicle_accessory`. The marketing model name (when present) is the stable key: `cobra:<model>`.

## Examples

| Capture | Inference |
|---|---|
| local name `"RAD 480i"` + primary UUID | model = `RAD 480i`, class = `radar_detector` |
| local name `"SC 220"` + primary + companion UUIDs | model = `SC 220`, class = `dashcam` |
| primary UUID only, no name | matched on UUID; class falls back to `vehicle_accessory` |

## References

- [Cobra Drive Smarter app](https://www.cobra.com/pages/drive-smarter-app)
- [Cobra RAD 480i product page](https://www.cobra.com/products/rad480i)
- [Cobra SC 220C product page](https://www.cobra.com/products/sc-220c)
