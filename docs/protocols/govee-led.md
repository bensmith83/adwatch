# Govee LED Light Strips and Bulbs

## Overview

Govee LED light strips and smart bulbs broadcast BLE advertisements for setup and local control via the Govee Home app. These are WiFi+BLE consumer LED products — BLE is used for initial configuration and direct local control when WiFi is unavailable. This protocol covers the LED lighting product line, which is distinct from Govee temperature/humidity sensors (handled by the existing `govee.py` parser with company ID `0xEC88`).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `Govee_HXXXX_XXXX` | e.g. `Govee_H618A_1234` |
| Local name | `GBK_HXXXX_XXXX` | Alternate branding prefix |
| Local name | `ihoment_HXXXX_XXXX` | Legacy branding (pre-Govee rebrand) |
| Manufacturer data | varies | Company IDs include `0x8843`, `0x8802`, and others |

LED devices do NOT use company ID `0xEC88`, which is reserved for Govee temperature and humidity sensors. The local name pattern with an embedded `HXXXX` model number is the primary identification signal.

### Local Name Patterns

```
Govee_H{model}_{device_id}
GBK_H{model}_{device_id}
ihoment_H{model}_{device_id}
```

Examples: `Govee_H618A_7B3F`, `GBK_H6022_A1C0`, `ihoment_H6114_52DE`

The model number (`HXXXX`) identifies the specific LED product. The suffix is a short hex device identifier.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | local_name | Govee LED device nearby |
| Model number | local_name | `HXXXX` pattern, e.g. `H618A` |
| Device ID | local_name suffix | Short hex identifier after the model |
| Brand variant | local_name prefix | `Govee`, `GBK`, or `ihoment` |

### What We Cannot Parse (requires GATT)

- Current color (RGB values)
- Brightness level
- Active scene or effect
- Power on/off state
- WiFi connection status
- Firmware version
- Music sync mode

## Device Class

```
led_light
```

## Known Models

| Model | Product | Notes |
|-------|---------|-------|
| H618A | LED Strip Light | WiFi + BLE RGBIC strip |
| H618F | LED Strip Light | WiFi + BLE RGBIC strip variant |
| H6022 | LED Light Bulb | Smart WiFi + BLE bulb |
| H6110 | Glide Hexa Light Panels | Hexagonal wall panels |
| H6114 | Glide Wall Light | LED wall light bar |
| H614E | LED Strip Light | WiFi + BLE strip |
| H805C | Outdoor LED String Lights | Permanent outdoor lights |

## Parser Coexistence with Govee Sensors

The existing `govee.py` parser handles Govee temperature and humidity sensors using:
- Company ID `0xEC88` (Govee sensor line)
- Local name pattern `^(GVH5|GV5124|Govee)`

A Govee LED parser must avoid conflicting with the sensor parser:
- LED devices use different company IDs (`0x8843`, `0x8802`, etc.) — never `0xEC88`
- The sensor parser's `^Govee` pattern will match some LED local names, so the LED parser should handle models that the sensor parser rejects (i.e., names containing `H618A`, `H6022`, etc. that do not carry sensor data in manufacturer_data)
- Routing should check for the `HXXXX` model pattern in the local name to distinguish LED products

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

## Detection Significance

- Consumer smart lighting — indicates a home with Govee LED products
- Multiple naming conventions (`Govee_`, `GBK_`, `ihoment_`) reflect brand evolution
- Devices broadcast continuously for app discovery and local BLE control
- WiFi+BLE dual connectivity — BLE is the fallback when cloud/WiFi is unavailable

## References

- [Govee Home App](https://www.govee.com/govee-app) — device control app
- [Govee Product Catalog](https://www.govee.com/) — LED lighting product line
