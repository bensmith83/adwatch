# Nordic Thingy:52 (Dev Kit Sensor Platform)

## Overview

The Nordic Thingy:52 is a development kit / reference design from Nordic Semiconductor featuring environment sensors, motion sensors, sound, and LED — all accessible via BLE GATT. The advertisement itself contains minimal data; all sensor readings require a GATT connection.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0059` | Nordic Semiconductor (in scan response) — shared by all Nordic devices |
| Service UUID | `EF680100-9B35-4933-9B10-52FFA9740042` | Thingy Configuration Service (in primary advertisement) |
| Local name | `Thingy` | Default name (configurable up to 10 chars) |

### Advertisement Data (primary)

- Flags: LE General Discoverable
- Complete Local Name: device name (default `"Thingy"`)
- Incomplete List of 128-bit Service UUIDs: Configuration Service UUID

### Scan Response Data

- Manufacturer Specific Data:
  - Company ID: `0x0059` (Nordic Semiconductor)
  - Data: 4-byte random device ID (reversed byte order, generated at boot via RNG)

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Thingy device present | service UUID match | Nordic Thingy:52 nearby |
| Device name | local_name | User-configurable |
| Random device ID | manufacturer_data bytes 0–3 | Regenerated at boot |

### What We Cannot Parse from Advertisements

All sensor data requires GATT connection and notification subscription:
- Temperature, pressure, humidity (Environment Service `0x0200`)
- Air quality — eCO2, TVOC (Environment Service `0x0204`)
- Color sensor — RGBC (Environment Service `0x0205`)
- Motion — accelerometer, gyroscope, compass, quaternion, step counter (Motion Service `0x0400`)
- Sound — microphone, speaker (Sound Service `0x0500`)
- Battery level (standard `0x180F`)
- Button state (UI Service `0x0300`)

### GATT Service Architecture

All custom services share base UUID `EF68xxxx-9B35-4933-9B10-52FFA9740042`:

| Service | Short UUID | Description |
|---------|-----------|-------------|
| Configuration | `0x0100` | Device name, advertising params, Eddystone URL, FW version |
| Environment | `0x0200` | Temperature, pressure, humidity, gas, color |
| User Interface | `0x0300` | LED control, button events, external pins |
| Motion | `0x0400` | Accelerometer, gyro, compass, step counter, orientation |
| Sound | `0x0500` | Microphone, speaker |
| Battery | `0x180F` | Standard BLE battery service |

## Detection Significance

- Nordic Semiconductor development kit — indicates a developer/tinkerer nearby
- Can optionally broadcast Eddystone-URL beacons in parallel
- The Thingy:91 (LTE/cellular) uses different firmware and does not share the `EF68xxxx` service architecture

## References

- **Nordic Thingy:52 FW**: https://github.com/NordicSemiconductor/Nordic-Thingy52-FW
- **Nordic Infocenter**: https://infocenter.nordicsemi.com/topic/ug_thingy52/
