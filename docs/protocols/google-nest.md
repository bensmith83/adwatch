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

## Future Work

- Determine if manufacturer_data or service_data on `0xFEAF` contains product type encoding
- Check if there are distinguishable patterns between Nest product categories
- Map local_name code patterns to device types (if any pattern exists)

## References

- [Bluetooth SIG — Service UUID 0xFEAF](https://www.bluetooth.com/specifications/assigned-numbers/) (assigned to Nest Labs Inc.)
