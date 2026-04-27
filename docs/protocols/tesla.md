# Tesla BLE Protocol

## Overview

Two distinct BLE surfaces:

1. **Vehicle phone-as-key** — every Tesla vehicle broadcasts an always-on
   pairing/recognition advertisement when parked/locked. Uses a 16-bit
   service UUID and a structured device name. *No manufacturer data.*

2. **Non-vehicle Tesla product** — at least one Tesla product (likely
   Powerwall, Wall Connector, or an accessory) advertises with the
   SIG-registered Tesla company ID `0x022B` in manufacturer data. The
   exact product is not yet pinned down; live captures suggest it's a
   stationary product (gas station / supercharger context observed).

The two paths are mutually exclusive in observed data — no Tesla vehicle
has been seen using mfr-data, and the non-vehicle product does not use
the `0x1122` service UUID.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID (vehicle) | `0x1122` (16-bit, SIG base) | Always-on phone-key beacon |
| Local name (vehicle) | `^S[A-Za-z0-9]{2}[3YSXCRDP]…` | Position-3 = model class char |
| Company ID | `0x022B` | SIG-registered to **Tesla, Inc.** — non-vehicle path |

## Ad Formats

### Vehicle Phone-Key (per `apk-ble-hunting/reports/teslamotors-tesla_passive.md`)

```
Service UUIDs: [0x1122]
Local name:    "S<2-char-prefix><model><VIN-hash-tail>"
Manufacturer data: not present
```

Device-name encoding:

| Position | Content | Meaning |
|----------|---------|---------|
| 0 | `S` | Literal prefix |
| 1-2 | 2 chars | Unknown — possibly hash prefix or protocol version |
| 3 | 1 char | Model class — `3`/`Y`/`S`/`X`/`C`/`R`/`D`/`P` |
| 4-N | rest | VIN-derived stable identifier (used for re-recognition) |

The position-3 model-char filter is what keeps this from matching every
S-prefixed device (Samsung, Sonos, SPRK+, …). Stable per-vehicle identity
comes from `name[3:]` — the VIN-hash tail.

### Non-Vehicle Product (live capture)

```
Manufacturer data (5 bytes): 2B 02 01 FE 03

Offset  Bytes      Meaning
  0-1   2B 02      Company ID 0x022B (LE)
  2     01         Unknown (type / version?)
  3     FE         Unknown
  4     03         Unknown
```

A single capture so far. Without more samples we can't decode the 3-byte
body. Working hypotheses (not confirmed):

- Powerwall / Powerwall 3 — local commissioning beacon
- Tesla Wall Connector (Gen 3 / Gen 4) — public-charger discoverability
- A vehicle accessory we haven't reverse-engineered

The parser tags this path as `device_class="energy"` (Powerwall and Wall
Connector are both energy products — closest fit in our shared device-class
vocabulary) with `product_kind="non_vehicle"` in metadata until further
captures distinguish them.

## Parsing Strategy

1. Match on **any** of: service UUID `0x1122`, device-name regex,
   or company ID `0x022B`
2. Vehicle path (UUID or name regex) takes precedence — a Tesla vehicle
   that one day starts emitting mfr-data is still a vehicle
3. Stable identity from VIN-hash tail when available; fall back to MAC
4. Tag `device_class="vehicle"` for the vehicle path, `"energy"`
   (with `product_kind="non_vehicle"` metadata) for the CID-only path

## Identity Hashing

```
# Vehicle (preferred — stable across MAC rotations):
identifier = SHA256("tesla:{vin_hash_fragment}")[:16]

# Non-vehicle / vehicle without name:
identifier = SHA256("tesla:{mac}")[:16]
```

## What We Cannot Parse

- VIN itself (only a hash fragment in the name)
- Vehicle state (locked / charging / driving)
- Wall Connector / Powerwall telemetry (charge rate, dispatch state)
- Any encrypted phone-key auth payload

## References

- `apk-ble-hunting/reports/teslamotors-tesla_passive.md`
- [Bluetooth SIG company ID assignments — 0x022B = Tesla, Inc.](https://www.bluetooth.com/specifications/assigned-numbers/)
- Source: APK static analysis + live NRF Connect capture (2026-04-26)
