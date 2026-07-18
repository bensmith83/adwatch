# Sub-Zero Group connected appliances (Sub-Zero / Wolf / Cove)

## Overview

Sub-Zero Group, Inc. — parent of the **Sub-Zero** (refrigeration), **Wolf**
(cooking), and **Cove** (dishwashers) premium kitchen brands — ships
connected appliances that pair with the "Sub-Zero Group Owner's App" over BLE
("Pair Via Bluetooth" / "Bluetooth Only Mode" in the vendor support pages).
The appliances advertise continuously with a GAP local name of the form
`SZG <retail model>`, where the model is the catalog number with slashes
stripped.

Captured models both resolve exactly to real products:

| Local name | Product |
|------------|---------|
| `SZG CL3650UFDID` | Sub-Zero Classic 36" French Door Refrigerator/Freezer with Internal Dispenser |
| `SZG SO3050PMSP` | Wolf SO3050PM/S/P — 30" M Series Professional Built-In Single Oven |

Two different brands under one `SZG` prefix pins **SZG = Sub-Zero Group**.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x1010` | **Not** SIG-assigned — pseudo/vanity CID (registry gap) |
| Header shape lock | mfr bytes 2-4 == `00 06 80` | Required; the pseudo-CID alone is not vendor-proof |
| Local name | `^SZG ` | Present only in the scan-response merged frame |

`0x1010` falls in an unassigned gap of the SIG company-ID registry (which tops
out at `0x10E1`), so it proves nothing on its own — the parser requires the
constant `00 06 80` header before attributing the frame. The value is
palindromic, so LE/BE byte order is moot.

The device also advertises the 128-bit service UUID
`E20A39F4-73F5-4BC4-A12F-17D1AD07A961`. This is Apple's archived
`BTLE_Transfer` sample-code "TransferService" UUID copied verbatim into the
firmware — a fingerprint, but **not** a safe routing key (any app derived
from Apple's sample would collide). It is distinct from the mutated variant
`…-1864-…a962` that `VolvoParser` matches inside iBeacon frames.

### Manufacturer data layout

iOS concatenates the ADV manufacturer data (8 bytes) with a second
manufacturer-data AD carried in the scan response (6 more bytes), so the same
device appears as either an 8-byte or a 14-byte frame; the 8-byte form is an
exact prefix of the 14-byte form.

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| 0 | 2 | Pseudo company ID | `10 10` |
| 2 | 2 | Header | `00 06` constant |
| 4 | 1 | Header | `80` constant |
| 5 | 3 | Device ID | Stable per physical unit |
| 8 | 1 | Scan-rsp marker | `0x11` (14-byte form only) |
| 9 | 2 | Model code | `0b 02` = CL3650UFDID, `0f 01` = SO3050PMSP |
| 11 | 3 | Constant | `03 05 05` (version-like; not enforced) |

The model code tracks the **model, not the unit**: two physically distinct
CL3650UFDID fridges carried byte-identical model codes. Keep it as an
extensible lookup — only two entries are known so far.

### Captured frames

| local name | mfr data |
|------------|----------|
| `SZG CL3650UFDID` | `10 10 00 06 80 32 d1 bd 11 0b 02 03 05 05` |
| `SZG CL3650UFDID` | `10 10 00 06 80 32 c9 2a 11 0b 02 03 05 05` |
| `SZG SO3050PMSP` | `10 10 00 06 80 32 dd 32 11 0f 01 03 05 05` |
| (none) | `10 10 00 06 80 2f ae 5f` |

## What We Can Parse

- Vendor (Sub-Zero Group) and, when named, the exact retail model
- `device_id` — stable 3-byte per-appliance identifier
- `model_code` — model/category code from the scan response

## What We Cannot Parse

- Appliance state (temperatures, modes, alarms) — GATT/cloud-side, not advertised
- Semantics of the `80` flag byte or the `03 05 05` tail
- Cove dishwashers (no capture yet)

## Parser scope

Passive presence, brand, model, and per-device ID only. `SubZeroGroupParser`
routes on pseudo-CID `0x1010` (with the header shape lock) and on the `SZG `
local-name prefix, so it identifies both the ADV-only and named forms.

## Confidence / attribution

**High** for the brand and the two named models (exact catalog matches across
two Sub-Zero Group brands, BLE pairing documented by the vendor). The frame's
undecoded fields (`80` flag, `03 05 05` tail) are honestly marked. Sighting
recurrence is modest — one 53-second encounter — but spans 4 distinct
physical devices, which clears the bar.

## References

- subzero-wolf.com — Owner's App Bluetooth pairing / "Bluetooth Only Mode" support pages
- Sub-Zero CL3650UFDID and Wolf SO3050PM/S/P retail product pages
- First seen: NearSight fresh-eyes telemetry sweep, 2026-07-01 (1 encounter, 7 records, 4 devices)
