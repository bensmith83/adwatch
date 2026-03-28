# TP-Link Tapo/Kasa Plugin

## Overview

TP-Link Tapo and Kasa are popular smart home product lines including smart plugs, bulbs, cameras, and sensors. These devices use BLE advertisements during setup/provisioning and intermittently for device discovery. TP-Link is one of the top-selling smart home brands on Amazon.

## Supported Devices

| Product Line | Local Name Pattern | Type |
|-------------|-------------------|------|
| Tapo Smart Plug | `Tapo_*` or `TP-*` | Smart plug (P100, P105, P110, P115) |
| Tapo Smart Bulb | `Tapo_*` | Smart bulb (L510E, L530E, L630) |
| Tapo Smart Camera | `Tapo_*` | Camera (C200, C210, C310) |
| Tapo Smart Hub | `Tapo_*` | Hub (H100, H200) |
| Tapo Sensor | `Tapo_*` | Sensors (T100, T110, T310, T315) |
| Kasa Smart Plug | `Kasa_*` or `HS*` or `KP*` | Legacy Kasa line |
| Kasa Smart Bulb | `Kasa_*` or `KL*` | Legacy Kasa line |

## BLE Advertisement Format

### Identification

TP-Link devices can be identified by:

1. **Local Name Pattern**: Starts with `Tapo` or `Kasa` (during BLE provisioning)
2. **Manufacturer Data**: TP-Link company ID in manufacturer data (company varies by chipset)
3. **Service UUID**: Some models use `0xFFF0` or custom UUIDs during setup

Best match strategy: `local_name_pattern=r"(?i)^(Tapo|Kasa|TP-LINK)"`.

### Advertisement Behavior

- **During setup**: Devices advertise continuously with local name containing model info
- **After WiFi setup**: Most devices stop BLE advertising (WiFi takes over)
- **Hub sensors**: Tapo H100/H200 hub sensors may continue BLE advertising for the sub-sensor protocol
- **Tapo T-series sensors**: Temperature/humidity sensors (T310, T315) advertise BLE data to the hub

### Manufacturer Data

When present, manufacturer data typically contains:
```
Offset  Length  Field           Description
0       2       Company ID      TP-Link vendor code
2       1       Device Type     Product category
3       var     Model Info      Model-specific data
```

### Parser Scope

The parser extracts:
- Device model/product line from local_name
- Product category (plug, bulb, camera, sensor, hub)
- Setup state detection (advertising = in setup mode)
- Device identifier from name suffix

Note: Most Tapo/Kasa communication is WiFi-based. BLE is primarily for provisioning. The parser identifies devices and their setup state.

## References

- [python-kasa](https://github.com/python-kasa/python-kasa) — Python library for TP-Link devices
- [TP-Link Tapo Protocol](https://github.com/mihai-dinculescu/tapo) — Rust library with protocol details
- [Home Assistant TP-Link Integration](https://www.home-assistant.io/integrations/tplink/)
