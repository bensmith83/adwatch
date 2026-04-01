# Shelly BLU Plugin

## Overview

Shelly BLU is a line of Bluetooth Low Energy sensors and buttons from Allterco Robotics (makers of Shelly smart home devices). Devices include door/window sensors, motion sensors, buttons, and environmental sensors. They broadcast sensor data via BLE advertisements using the BTHome v2 format, but also include Allterco-specific manufacturer data with additional device info.

## Supported Devices

| Model | Local Name Pattern | Type |
|-------|-------------------|------|
| BLU Button1 | `SBBT-002C` | Button with temperature/humidity |
| BLU Door/Window | `SBDW-002C` | Contact sensor |
| BLU Motion | `SBMO-003Z` | PIR motion sensor with lux |
| BLU H&T | `SBHT-003C` | Temperature/humidity sensor |
| BLU RC Button 4 | `SBBT-004CEU` | 4-button remote |
| BLU Wall Switch 4 | `SBWS-*` | Wall switch |
| BLU Micro | -- | Tiny automation module |

Additional models follow the `SB*` naming pattern.

## BLE Advertisement Format

### Identification

Shelly BLU devices can be identified by:

1. **Company ID**: `0x0BA9` (Allterco Robotics Ltd, decimal 2985)
2. **Local Name Pattern**: Starts with `SB` (e.g., `SBBT-002C`, `SBDW-002C`, `SBMO-003Z`)
3. **Service UUID**: `0xFCD2` (BTHome) — present when broadcasting sensor data

Best match strategy: company_id `0x0BA9` OR local_name_pattern `^SB[A-Z]{2}-`.

### Manufacturer Data (Company ID 0x0BA9)

```
Offset  Length  Field           Description
0       1       Device Type     Model identifier byte
1       1       Packet Counter  Rolling counter (0-255), for dedup
2       1       Battery         Battery level (0-100%)
3+      var     Encrypted?      Optional encrypted payload (if encryption enabled)
```

### BTHome v2 Service Data (UUID 0xFCD2)

Shelly BLU devices broadcast sensor readings using BTHome v2 format on service UUID `0xFCD2`. The existing BTHome parser already handles this. The Shelly-specific parser adds:

- Device model identification from local name
- Battery level from manufacturer data
- Packet counter for deduplication
- Device type classification

### Sensor Data Available

| Device | Data Fields |
|--------|------------|
| Button | button_event, temperature, humidity, battery |
| Door/Window | contact (open/closed), battery |
| Motion | motion (detected/clear), illuminance (lux), battery |
| H&T | temperature, humidity, battery |

## Parser Strategy

- Register with `company_id=0x0BA9` and `local_name_pattern=r"^SB[A-Z]{2}-"`
- Extract device model from local_name
- Parse manufacturer data for battery, packet counter
- Note: BTHome service data is handled by existing bthome parser; this parser focuses on the Allterco-specific manufacturer data and device identification
- Return ParseResult with device_type, model, battery, packet_counter

## References

- [Shelly BLU API Docs](https://shelly-api-docs.shelly.cloud/docs-ble/)
- [BTHome v2 Format](https://bthome.io/format/)
- [Home Assistant Shelly BLU Integration](https://www.home-assistant.io/integrations/shelly/)
