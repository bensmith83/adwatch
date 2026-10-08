# QuietCool Smart Attic Fan (IT-AF-SMT)

## Overview

QuietCool ships a BLE-controlled smart attic fan (model **IT-AF-SMT** /
"Smart Attic Fan Control") that pairs with the QuietCool mobile app over
BLE. The controller broadcasts continuously while powered.

The advertisement is identification + presence only — live state (fan
speed, schedule, runtime, temperature thresholds) lives behind the
QuietCool GATT profile.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x4733` | NOT a BT SIG assignment — vanity; LE bytes `33 47` = ASCII `"3G"` (firmware-generation marker) |
| Local name | `ATTICFAN_<12 hex>` | The 12-hex suffix is the controller's BD_ADDR with colons stripped |

The parser accepts either signal alone. The `<12 hex>` suffix is the
stable per-unit identity (survives random-address rotation).

## Wire Format

Manufacturer payload (after the 2-byte CID, captures consistently emit
25 bytes — a 19-byte ASCII string + 6 NUL pads):

```
33 47 | xx xx xx xx xx 27 73 20 41 74 74 69 63 20 46 61 6e | 00 00 00 00 00 00
       └──────────────── "<name>'s Attic Fan" ─────────────┘
```

Reading the CID + payload as a single ASCII run produces a possessive
`"<name>'s Attic Fan"` string (name redacted here). It may be an internal
QuietCool / ODM codename or a user-assigned fan name — only one unit has
been captured, so this is unresolved. If it is user-assigned, the leading
CID bytes (`"3G"`) may also vary per unit. The leading `3` is otherwise
plausibly the firmware/hardware revision.

## Captured Examples

```
localName = "ATTICFAN_xxxxxxxxxxxx"
mfr       = 33 47 xx xx xx xx xx 27 73 20 41 74 74 69 63 20 46 61 6e 00 00 00 00 00 00
```

Captured 2026-05-28 in `research/adwatch_export 14.json` — 1 device,
255 sightings. OUI `34:94:54` is unallocated in IEEE space; the
controller likely uses an ESP32 or similar SoC with a vendor-assigned
local MAC.

## Identity Hashing

```
identifier_hash = SHA256("quietcool_attic_fan:suffix:<12 hex>")[:16]   # when ATTICFAN_ name matches
identifier_hash = SHA256("quietcool_attic_fan:mac:<MAC>")[:16]         # fallback
```

## What We Cannot Parse Without GATT

- Fan speed (low/medium/high)
- Runtime hours
- Schedule
- Attic temperature reading
- Firmware version
- Whether the fan is currently running

## References

- [rwarner/ha-quietcool-ble (Home Assistant integration — documents the `ATTICFAN_` localName pattern)](https://github.com/rwarner/ha-quietcool-ble)
- [QuietCool IT-AF-SMT Owner's Guide PDF](https://quietcoolsystems.com/wp-content/uploads/2024/08/IT-AF-SMT-Owners-Guide-6-30-23-Web.pdf)
- [QuietCool Smart Attic Fan Control product page (Home Depot)](https://www.homedepot.com/p/QuietCool-Wireless-Smart-Control-For-Attic-Fans-IT-AF-SMT/321550100)
