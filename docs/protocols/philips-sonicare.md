# Philips Sonicare (Electric Toothbrush)

## Overview

Philips Sonicare smart toothbrushes broadcast BLE advertisements to enable pairing with the Sonicare app for brushing habit tracking. They are identified by their `local_name` ("Philips Sonicare") and custom service UUIDs in the `477ea6xx` range.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `Philips Sonicare` | Stable, always present |
| Service UUIDs (advertised) | `477ea600-a260-11e4-ae37-0002a5d50001` | Primary Sonicare service |
| | `477ea600-a260-11e4-ae37-0002a5d50002` | Secondary service |
| | `477ea600-a260-11e4-ae37-0002a5d50004` | Additional service |
| | `477ea600-a260-11e4-ae37-0002a5d50005` | Additional service |
| | `a651fff1-4074-4131-bce9-56d4261bc7b1` | Firmware/OTA service |

The UUID base `477ea600-a260-11e4-ae37-0002a5d5xxxx` is unique to Philips Oral Healthcare (OHC) devices.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | local_name match | Sonicare toothbrush is nearby |
| Service UUIDs | service_uuids list | Identifies it as a Philips OHC device |

### What We Cannot Parse (requires GATT)

- Toothbrush model (e.g. HX9120)
- Serial number
- Firmware version
- Battery level
- Brushing session data

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

## Known Models Observed

| GATT Model ID | Product |
|--------------|---------|
| HX9120 | Philips Sonicare DiamondClean |

## Detection Significance

- Consumer IoT device — indicates a bathroom/personal space
- Broadcasts even when not actively brushing (for app connectivity)
- The `477ea6xx` UUID family is a reliable fingerprint for Philips OHC devices

## Future Work

- Determine if manufacturer_data contains model or state information in advertisements
- Check if advertisement payload changes during active brushing sessions
- Catalog UUID family across different Sonicare models

## References

- [Philips Sonicare App](https://www.philips.com/sonicare) — companion app documentation
