# Owlet Baby HR/SpO2 Monitor BLE Protocol

## Overview

Owlet Baby Care makes the **Smart Sock** and **Dream Sock** — wearable baby
heart-rate and pulse-oximetry monitors. The sock pairs to a base station
over BLE and relays data to a phone app.

A passive scanner sees the device while it's broadcasting in pair-mode or
companion-app range; live operational data is not in the advertisement.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0E9F` | SIG-registered to **Owlet Baby Care Inc.** |
| Service UUID | `c5163c4b-9b63-570d-a3a8-407716f04276` | Custom 128-bit |
| Local name | `OB` | Short — never match on this alone |

The name "OB" is two characters and would collide with many other devices,
so the parser requires either the company ID or the service UUID and treats
the name as enrichment only.

## Ad Format

### Manufacturer Data (observed)

```
Offset  Bytes      Meaning
  0-1   9f 0e      Company ID 0x0E9F (LE)
  2-3   00 00      Reserved / state byte (always zero in observed captures)
```

Two captures had the identical 4-byte payload `9f 0e 00 00`. With more
samples the trailing bytes may resolve to a status field; for now we treat
the body as opaque.

### Service UUIDs

`c5163c4b-9b63-570d-a3a8-407716f04276` is co-advertised with the mfr data
when the device is in companion-mode. UUIDv5-like layout suggests it was
generated from a vendor namespace string.

## Detection Significance

- Owlet device in range — baby HR/SpO2 monitor
- Setup mode or active companion-mode use
- Persistent presence over hours/days = home installation

## Parsing Strategy

1. Match on company ID `0x0E9F` OR the custom service UUID
2. Tag `device_class="medical"`, `beacon_type="owlet"`
3. Record local name `OB` as enrichment if present

## Identity Hashing

```
identifier = SHA256("owlet:{mac}")[:16]
```

(Local-name enrichment doesn't carry a stable per-device identifier; MAC is
the only stable identity until/unless a serial number surfaces.)

## What We Cannot Parse

- Heart rate, SpO2, motion (GATT-only — not in advertisement)
- Battery level
- Sock pair status / firmware
- Per-device serial number

## References

- [Owlet Smart Sock product page](https://owletcare.com/products/smart-sock)
- [Bluetooth SIG company ID assignments — 0x0E9F = Owlet Baby Care Inc.](https://www.bluetooth.com/specifications/assigned-numbers/)
- Source: live capture (NRF Connect, 2026-04-26)
