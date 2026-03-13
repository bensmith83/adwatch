# RadonEye RD200 (Radon Detector)

## Overview

RadonEye RD200 is a consumer radon detector by FTLab/Ecosense. It broadcasts a distinctive local name containing serial number and region information. Radon readings require a GATT connection — this parser provides device detection and classification.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `FR:*` | Starts with `FR:` followed by version/region code + serial |
| Company ID | None registered | Uses generic chipset ID |

### Local Name Format

The local name encodes the device version and region:

| Prefix | Version | Notes |
|--------|---------|-------|
| `FR:R2*` | Version 1 | nRF5x chipset |
| `FR:RU*` | Version 2 (USA) | ESP32 chipset |
| `FR:RE*` | Version 2 (Spain) | ESP32 chipset |
| `FR:GI*` | Version 2 | Regional variant |
| `FR:H*` | Version 2 | Regional variant |
| `FR:GL*` | Version 2 | Regional variant |
| `FR:I*` | Version 2 | Regional variant |
| `FR:J*` | Version 2 | Regional variant |
| `FR:RD*` | Version 2 | Regional variant |
| `FR:GJ*` | Version 2 | Regional variant |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | Local name pattern | RadonEye nearby |
| Version | Local name prefix | V1 vs V2 |
| Region | Local name prefix | USA, EU, etc. |
| Serial hint | Local name suffix | Partial serial number |

### What Requires GATT Connection

- Radon level (pCi/L, IEEE 754 float)
- Reading requires: connect → write `0x50` to characteristic → read response bytes 3-6

### GATT Service UUIDs (for reference)

| Version | Service UUID |
|---------|-------------|
| V1 | `00001523-1212-efde-1523-785feabcd123` |
| V2+ | Varies (ESP32-based, some UUID changes) |

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

## Detection Significance

- Indicates radon monitoring concern (common in certain geographies)
- Version/region extraction from name is useful metadata
- V1 vs V2 hardware distinction

## References

- [ESPHome RadonEye](https://esphome.io/components/sensor/radon_eye_ble/) — ESPHome component
