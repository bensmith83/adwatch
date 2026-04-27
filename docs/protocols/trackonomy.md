# Trackonomy Systems BLE Protocol

## Overview

[Trackonomy Systems](https://trackonomy.io/) makes disposable BLE/cellular
"smart sticker" asset trackers used in shipping, logistics, and supply-chain
monitoring. Their hardware family includes TrackPack, Wing, and various
peel-and-stick label-shaped tags that report location and condition.

A passive scanner near a freight hub, gas station, or warehouse may pick
these up incidentally. The advertisement payload format is proprietary and
not documented publicly; detection is by SIG company ID alone.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0EF7` | SIG-registered to **Trackonomy Systems, Inc.** |

No published device-name pattern, no public service UUID — CID is the only
reliable passive signal.

## Ad Format

### Manufacturer Data (observed)

```
Offset  Bytes                           Meaning
  0-1   f7 0e                            Company ID 0x0EF7 (LE)
  2-N   xx..xx                           Vendor-proprietary payload
```

Single observed capture (13-byte body):
```
f7 0e 49 56 e2 9f 84 21 1e 44 ff b5 1e
```

The body looks random across the bytes we've seen; without more captures
or app reverse-engineering we can't decode internal fields. Possible
contents (speculation): tag-id hash, sequence counter, power/state flags,
a short sensor reading.

## Detection Significance

- Trackonomy asset tag in range — freight, parcel, or pallet tracker
- Indicates an active shipment or staged inventory nearby
- Tags are battery-powered and disposable — short useful life

## Parsing Strategy

1. Match on company ID `0x0EF7` (only signal)
2. Tag `device_class="asset_tracker"`, `beacon_type="trackonomy"`
3. Record manufacturer-data body as `raw_payload_hex` for later analysis

## Identity Hashing

```
identifier = SHA256("trackonomy:{mac}")[:16]
```

## What We Cannot Parse

- Tag serial number / shipment ID
- Sensor telemetry (temperature, shock, tilt — if present)
- Battery level
- Cellular-side state

## References

- [Trackonomy product family](https://trackonomy.io/products/)
- [Bluetooth SIG company ID assignments — 0x0EF7 = Trackonomy Systems, Inc.](https://www.bluetooth.com/specifications/assigned-numbers/)
- Source: live capture at a gas station (NRF Connect, 2026-04-26)
