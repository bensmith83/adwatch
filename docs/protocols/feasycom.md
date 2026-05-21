# Feasycom Plugin

## Overview

**Feasycom Co., Ltd** (Shenzhen) is an OEM Bluetooth-module vendor. The
**FSC-BT** family (FSC-BT1026, FSC-BT909, FSC-BT986, FSC-BT630, …) is a
chip-down module embedded inside a wide variety of consumer and industrial
products — audio adapters, IoT widgets, automotive accessories, POS
terminals, and so on.

Critically, the advertisement this parser matches is the **module's** factory
signature, not anything chosen by the host product. We therefore surface
`device_class = ble_module` and explicitly note that the host product is
unknown. If you correlate a `feasycom:FSC-BT1026C` stable key with a
physical product label, that mapping lives in user observation, not in the
advertisement itself.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Manufacturer-data CID | `0x0A2D` (little-endian raw bytes `2d 0a`) — Feasycom Co., Ltd, per [Bluetooth SIG assigned numbers](https://www.bluetooth.com/specifications/assigned-numbers/) |
| Service UUID (16-bit) | `FFF0` (generic; many unrelated vendors squat on this — we do **not** rely on it for identification) |
| Local name | `FSC-BT<sku>[-LE]` — e.g. `"FSC-BT1026C-LE"`, `"FSC-BT986"` |
| Sample mfr-data hex | `2d0add0d307d7b32` (CID `2d 0a` + 6-byte payload) |

A device matches if **either** the manufacturer-data company ID is
`0x0A2D` **or** the GAP local name matches
`^FSC-BT[0-9]{3,4}[A-Z]?(-LE)?$`. The `FFF0` service UUID is too generic
to be a routing signal on its own.

### Payload Layout (6-byte tail after CID)

| Offset | Bytes (sample 1) | Bytes (sample 2) | Notes |
|---|---|---|---|
| `0..4` | `dd 0d 30 7d 7b` | `dd 0d 30 7d 7b` | Stable across sightings of the same physical module. Most likely a MAC suffix or factory serial fingerprint. |
| `5` | `32` | `28` | Varies between consecutive captures from the same module. Most likely a status / counter / state-flag byte. |

We do not interpret these further; the entire 6-byte tail is exposed as
`payload_hex` in the metadata so downstream consumers can correlate
sightings of the same physical module.

### SKU Extraction

The local-name regex captures the module SKU as the prefix up to (but not
including) the optional `-LE` low-energy-role suffix:

| Local name | Captured SKU | Stable key |
|---|---|---|
| `FSC-BT1026C-LE` | `FSC-BT1026C` | `feasycom:FSC-BT1026C` |
| `FSC-BT1026C` | `FSC-BT1026C` | `feasycom:FSC-BT1026C` |
| `FSC-BT986` | `FSC-BT986` | `feasycom:FSC-BT986` |

Stripping `-LE` collapses the BLE-role variant onto the dual-mode SKU so
both advertise into the same stack.

## Examples

| Capture | Inference |
|---|---|
| local name `"FSC-BT1026C-LE"` + mfr `2d0add0d307d7b32` + UUID `FFF0` | sku = `FSC-BT1026C`, class = `ble_module`, payload_hex = `dd0d307d7b32` |
| mfr `2d0add0d307d7b28` only (no name) | matched on CID 0x0A2D; class = `ble_module`; no SKU; payload_hex = `dd0d307d7b28` |
| local name `"FSC-BT986"` only | matched on name regex; sku = `FSC-BT986`; no payload_hex |

## References

- [Bluetooth SIG assigned numbers — company identifiers](https://www.bluetooth.com/specifications/assigned-numbers/) (entry `0x0A2D` = Feasycom Co., Ltd)
- [Feasycom corporate page](https://www.feasycom.com/)
- [Feasycom FSC-BT1026 product page](https://www.feasycom.com/product/long-range-bluetooth-module-fsc-bt1026.html) — long-range BLE 5.x Class-1 module
