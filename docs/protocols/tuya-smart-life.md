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

### Cheap-Clone Pairing-Mode Name (no SIG-correct CID)

A large fraction of cheap WiFi+BLE smart plugs / bulbs sold on Amazon and
AliExpress use a Tuya-compatible firmware fork but **don't bother
emitting the SIG-registered Tuya company ID** — they advertise an
unregistered or arbitrary CID with malformed manufacturer data while
broadcasting a stable pairing-mode local name:

```
^Smart\.[A-Z0-9]{2}\.WIFI$
```

Observed example: `Smart.A5.WIFI` with mfr-data `<56 45 52 15>` (ASCII
`"VER\x15"` — clearly not a real CID payload). The two-character segment
varies per device.

Behaviorally these are Tuya pairing beacons, so the parser claims them
under the same name with `match_source="name_regex"` and
`pairing_mode_clone=True` so they're distinguishable from CID-path
matches in downstream queries.

### Parser Scope

The parser extracts:
- Protocol version from manufacturer data (CID path)
- Device flags (pairing state) (CID path)
- Product identifier if present (CID path)
- Presence detection
- Pairing-mode-clone tagging (name-regex path) — stamps
  `match_source="name_regex"`, `pairing_mode_clone=True`,
  `pairing=True` so a clone in pairing mode is still surfaced as a
  smart-home device

Note: Many Tuya devices only advertise BLE during setup/pairing. Sensor devices (thermometers, door sensors) may continuously broadcast.

## References

- [Tuya BLE SDK Guide](https://developer.tuya.com/en/docs/iot-device-dev/tuya-ble-sdk-user-guide?id=K9h5zc4e5djd9)
- [Theengs Decoder — Tuya devices](https://decoder.theengs.io/devices/devices.html)
- [BLE Monitor — Tuya sensors](https://custom-components.github.io/ble_monitor/by_brand)
