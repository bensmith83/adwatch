# Tuya / Smart Life Plugin

## Overview

Tuya is the platform behind hundreds of white-label smart home brands sold on Amazon (BlitzWolf, Moes, Zemismart, SmartLife, and many generic/no-name devices). Tuya devices use BLE advertisements for provisioning and, in some cases, broadcasting sensor data (temperature, humidity, door state, etc.).

## BLE Advertisement Format

### Identification

Tuya devices can be identified by:

1. **Company ID**: `0x07D0` (Tuya Inc / Hangzhou Tuya Information Technology, decimal 2000)
2. **Service UUID**: `0xA201` (Tuya BLE service, some devices) or `0xFD50` (newer Tuya devices)

Best match strategy: `company_id=0x07D0`.

### Manufacturer Data (Company ID 0x07D0)

```
Offset  Length  Field           Description
0       2       Company ID      0xD007 (LE) = 0x07D0
2       1       Protocol Ver    Tuya BLE protocol version
3       1       Flags           Device state flags (pairing mode, etc.)
4       var     Product ID      Variable-length product category identifier
```

### Common Tuya Device Categories

| Category | Products | BLE Behavior |
|----------|----------|-------------|
| Thermometer/Hygrometer | BTH01, TH05F, TH03Z | Continuous BLE broadcasting of temp/humidity |
| Door/Contact Sensor | Various | Event-based BLE advertising |
| Smart Plug | Various | BLE for provisioning only |
| Smart Bulb | Various | BLE for provisioning only |
| Motion Sensor | Various | Event-based BLE advertising |

### Parser Scope

The parser extracts:
- Protocol version from manufacturer data
- Device flags (pairing state)
- Product identifier if present
- Presence detection

Note: Many Tuya devices only advertise BLE during setup/pairing. Sensor devices (thermometers, door sensors) may continuously broadcast.

## References

- [Tuya BLE SDK Guide](https://developer.tuya.com/en/docs/iot-device-dev/tuya-ble-sdk-user-guide?id=K9h5zc4e5djd9)
- [Theengs Decoder — Tuya devices](https://decoder.theengs.io/devices/devices.html)
- [BLE Monitor — Tuya sensors](https://custom-components.github.io/ble_monitor/by_brand)
