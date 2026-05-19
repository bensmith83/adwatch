# TimoTwo Plugin

## Overview

**TimoTwo** is a Bluetooth Low Energy SoC module produced by **BlueRadios, Inc.** (Lafayette, Colorado), sold as a drop-in BLE radio for embedded products. Out-of-the-box, the module advertises with the local name `"TimoTwo"`, the BlueRadios default vendor service UUID, and manufacturer data tagged with the SIG-reserved CID `0xFFFF` (i.e. no real BLE SIG company assignment yet).

A `TimoTwo` sighting therefore identifies an unbranded / pre-production device — typically a developer eval board, a custom industrial sensor, or a finished product whose vendor never replaced the default module identity. The device itself is unknown, but the *radio* is identifiable.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Local name | `"TimoTwo"` |
| Service UUID (128-bit) | `33B5376D-0942-1F91-379B-AC5AF36B9EFA` |
| Company ID | `0xFFFF` (SIG reserved — module has no real CID assigned) |

Local name or service UUID is enough to match.

### Manufacturer Data Layout (9 bytes after the `0xFFFF` CID)

```
03 f1 40 00 00 4c 55 f1 40
```

The leading `03 f1 40` matches BlueRadios' published demo broadcast header; the trailing bytes are firmware-version / RSSI calibration fields that vary per build. The parser surfaces the whole payload verbatim as `payload_hex` because no public spec documents the byte-level layout.

## Stable Identity

There is no per-unit identifier in the advertisement. We key on the (rotating) BD_ADDR for the stable key, which means two sightings of the same physical device after a MAC rotation will look like two different devices — this is unavoidable until a vendor builds a real product around the module and gives it a real identity.

## References

- [BlueRadios TimoTwo product page (BR-LE4.0-S2A)](https://www.blueradios.com/products/)
- Captures in `research/adwatch_export 4.json` (search for service UUID `33B5376D-…` or local name `TimoTwo`)
