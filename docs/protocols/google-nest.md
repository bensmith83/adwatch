# Google Nest

## Overview

Google Nest devices (thermostats, cameras, speakers, displays, doorbells) broadcast BLE advertisements using service UUID `0xFEAF` (assigned to Nest Labs Inc.). This enables device setup via the Google Home app and local device discovery.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFEAF` | Nest Labs Inc. (BLE SIG assigned) |
| Local name | Short alphanumeric code | e.g. `NW3J0`, `NJXAS` — not human-readable |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Nest device present | service_uuid match | Google Nest device nearby |
| Device code | local_name | Short code, not a readable product name |

### What We Cannot Parse from Advertisements

- Specific product type (thermostat vs. camera vs. speaker)
- Device model or generation
- Setup state
- Any sensor readings

## Local Name Pattern

Nest devices use short alphanumeric codes as local names (e.g. `NW3J0`, `NJXAS`). These don't reveal the product type. The code may be derived from the device's serial number or setup token.

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

## Known Products Using 0xFEAF

| Product | Notes |
|---------|-------|
| Nest Thermostat | All generations |
| Nest Cam / Dropcam | Indoor/outdoor cameras |
| Nest Hub / Hub Max | Smart displays |
| Nest Mini / Audio | Smart speakers |
| Nest Doorbell | Video doorbell |
| Nest Protect | Smoke/CO detector |
| Google Home (legacy) | Rebranded to Nest |

## Detection Significance

- Smart home infrastructure device
- Broadcasts continuously (always-on BLE for Google Home app control)
- Common in residential environments
- Multiple Nest devices at one location is typical

## Service Data Format (17 bytes)

The FEAF service data payload is not publicly documented. Based on analysis of observed samples, the following partial structure has been inferred:

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| 0-1 | 2 | header | Constant `0x10 0x01` — likely protocol version or message type |
| 2 | 1 | unknown_1 | Constant `0x00` in all samples |
| 3 | 1 | device_type? | Constant `0x02` — possibly device category |
| 4-7 | 4 | variable_a | Changes between samples; possibly encodes device state (temperature, setpoint, mode) |
| 8-11 | 4 | variable_b | Highly variable; possibly a counter, timestamp, or nonce |
| 12 | 1 | unknown_2 | Constant `0x00` |
| 13-14 | 2 | variable_c | Changes between samples |
| 15 | 1 | variable_d | Changes between samples (`0x64`, `0x44`) |
| 16 | 1 | trailer | Constant `0x01` |

### Observed Samples

```
Sample 1: 10 01 00 02 00 e1 19 00  dc 0d 1c 52 00 66 16 64 01
Sample 2: 10 01 00 02 00 e1 19 00  54 63 13 52 00 66 16 64 01
Sample 3: 10 01 00 02 5a 23 17 00  f7 92 21 00 00 3b bb 44 01
```

Samples 1 and 2 share bytes 4-7 (`00e11900`) and bytes 13-15 (`661664`), suggesting the same device at different times. Sample 3 differs significantly (different device or state).

**Speculative temperature encoding**: If bytes 4-5 encode temperature as LE uint16 in tenths of a degree Celsius, `0x00E1` (225) = 22.5°C (72.5°F) — a plausible indoor thermostat reading. Unconfirmed.

The variable sections (bytes 8-11) may include encrypted or rolling-code elements. Nest devices use encryption for device-to-device communication (AES-based, via the Weave/Thread protocol stack).

## Observed in adwatch (April 2026 Export)

Six FEAF devices observed over ~18 days:

| Local Name | Sighting Count | Notes |
|------------|---------------|-------|
| `NJXAS` | 1,774 | Highest count; long-term continuous advertising |
| `NW3J0` | 1,766 | Similar count, likely co-located |
| `NNCQR` | ~hundreds | Regular advertising |
| `NRE6R` | ~hundreds | Regular advertising |
| `N00V6` | ~hundreds | Regular advertising |
| `N6TC1` | ~hundreds | Regular advertising |

All share: FEAF service UUID only (no manufacturer data), "N" + 4 alphanumeric local names, 17-byte service data, random address type. Very high sighting counts indicate mains-powered devices broadcasting continuously.

## Future Work

- Confirm temperature encoding hypothesis with controlled temperature measurements
- Determine if different Nest product types (thermostat vs Protect vs sensor) produce distinguishable service data patterns
- Map local_name code patterns to device types (if any pattern exists)

## References

- [Bluetooth SIG — Service UUID 0xFEAF](https://www.bluetooth.com/specifications/assigned-numbers/) (assigned to Nest Labs Inc.)
- [Nordic Semiconductor Bluetooth Numbers Database](https://github.com/NordicSemiconductor/bluetooth-numbers-database) — confirms FEAF = Nest Labs Inc
- [Google Nest Thermostat technical specs](https://support.google.com/googlenest/answer/9230098) — confirms BLE 5.0 support
