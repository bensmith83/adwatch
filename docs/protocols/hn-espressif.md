# HN_ Espressif Smart-Home Device

## Overview

A small fleet of BLE devices advertising local names of the form
`HN_ACCF23XXXXXX` — a literal `HN_` prefix followed by 12 hex
characters whose first 6 chars are the **Espressif Inc.** IEEE OUI
`AC:CF:23`. The advertisement carries no manufacturer or service
data; the name itself is the only useful payload.

The 12-hex suffix is the device's BLE / Wi-Fi MAC address verbatim,
exposed as the friendly name by stock Espressif SDK example code.
Seven distinct devices were captured in a single 2026 adwatch
session — consistent with a small home full of ESP-based smart
plugs, switches, or sensors.

## Two layers of vendor identification

| Layer | adwatch confidence | How |
|-------|--------------------|-----|
| **Silicon vendor** (`Espressif Inc.`) | **High** — exposed as `silicon_vendor` and `oui_vendor` | IEEE OUI lookup — the first three bytes of the MAC are a registered Espressif assignment, so the chip on board is unambiguously an ESP8266 / ESP32-family part. |
| **Product brand / OEM**               | **Low — not claimed** | The `HN_` name prefix narrows the candidate pool but is not unique. |

Working hypotheses for the **product brand** (none confirmed):

- **Honyar / Hangzhou Hangneng** — Chinese smart-switch and outlet
  brand sold under HN_ naming; ships ESP8266 / ESP32 internals.
- **Tuya / Smart Life white-label** flashed with an open firmware
  that defaults to `HN_<mac>` for its BLE name.
- A custom in-house automation project built on the Arduino /
  ESP-IDF defaults.

So the parser **does** make a vendor claim — for the **silicon** —
while staying honest that the **upstream product brand** is
unidentified. Further brand attribution requires a GATT connection
or open-source-firmware inspection.

## Identification

```
local_name: "HN_<12-hex>"
            └┬┘ └────┬───┘
            literal   BLE MAC; first 6 hex = OUI
service_uuids:    (none)
manufacturer_data: (none)
service_data:      (none)
```

Regex: `^HN_([0-9A-Fa-f]{12})$`

The parser additionally requires the first 6 hex characters to be
one of the known Espressif OUIs so we don't over-claim any future
device whose name happens to start with `HN_`.

Known Espressif OUIs the parser accepts (`silicon_family` value shown
on the right):

```
AC:CF:23   →  ESP8266 / ESP32 (legacy)
24:62:AB   →  ESP32-C3
84:F3:EB   →  ESP32-S3
24:0A:C4   →  ESP32
30:AE:A4   →  ESP32
FC:F5:C4   →  ESP32 (recent)
```

These chip-family hints reflect Espressif's dominant SKU under each
OUI block at time of writing; the family field is guidance only
since IEEE OUI blocks span multiple chip generations over time.

## Metadata Exposed

| Key | Example | Notes |
|-----|---------|-------|
| `device_mac` | `ac:cf:23:06:06:cb` | Full 6-byte MAC parsed from the name |
| `oui_vendor` | `Espressif Inc.` | Generic OUI-based vendor (silicon) |
| `silicon_vendor` | `Espressif Inc.` | Alias of `oui_vendor` — surfaced as a separate key so analytics can tell "silicon vendor (confident)" from "product brand (unknown)" |
| `silicon_family` | `ESP8266 / ESP32 (legacy)` | Per-OUI Espressif chip-family hint |

## Identity Hashing

```
identifier_hash = SHA256("hn_espressif:{device_mac}")[:16]
```

The device MAC (extracted from the name suffix) is the canonical
identity. It is stable across BLE-MAC rotation by definition — the
visible MAC IS the underlying hardware MAC.

## What We Cannot Parse Without GATT

- Vendor / model / firmware version (would come from the GATT
  Device Information service if exposed)
- Smart-home function — switch vs plug vs sensor vs bulb
- On/off state, dimmer level, sensor readings

A passive scanner can only count, group, and locate them by RSSI.

## Captured Devices (2026 export)

Seven distinct devices, all with `HN_ACCF23` prefix (Espressif OUI),
all within the same ~10 m radius. Possible deployment scenarios:

- a household with multiple Honyar smart outlets installed
- a small commercial space with ESP-flashed lighting controllers
- a project lab full of ESP32 dev kits

## Open Questions

- Which exact vendor / firmware base? If you recognize the `HN_`
  naming convention paired with `AC:CF:23` OUI, please open an
  issue with a vendor / SKU pointer.
