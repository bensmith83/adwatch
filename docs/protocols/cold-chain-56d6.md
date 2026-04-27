# Cold-Chain / Refrigerated-Shelf Sensor (UUID 56D63956 — vendor TBD)

## Overview

Generic shape-based parser for a custom 128-bit service UUID seen on
multiple devices in a small bespoke supermarket. The on-the-ground
hypothesis is that these are **temperature sensors mounted in
refrigerated shelves**; the advertisement only carries a stable
6-character ASCII sensor ID, which we believe is a back-end lookup key
— actual telemetry presumably flows over a separate channel or only on
GATT connect.

The vendor is not yet identified. The parser key is `cold_chain_56d6`
and is intentionally UUID-prefix-named so it can be renamed once the
vendor surfaces without disturbing detection logic.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `56d63956-93e7-11ee-b9d1-0242ac120002` | Custom 128-bit, full UUID required |

Notes about the UUID itself:

- It's a **UUIDv1** (variant + version bits in the third group `93e7-11ee`
  decode as version 1).
- Timestamp portion encodes **November 2023** — when this UUID was
  generated.
- The node field `0242ac120002` is **Docker's bridge-network MAC OUI**
  (`02:42:ac:*`) — strongly suggesting the UUID was generated
  programmatically inside a container by an in-house build pipeline.
  Common with small custom-software shops.

## Ad Format

### Service Data

```
Offset  Bytes      Meaning
  0     00         Constant leading byte (always zero in observed captures)
  1-6   xx..xx     6 ASCII chars [A-Z0-9] — sensor ID
```

Three observed sensor IDs (all from same store, same minute):

```
SSFYV3
1ZNQGY
LYHR3S
```

Pattern is uppercase letters and digits only — looks base32-ish.

The parser enforces strict shape: 7 bytes total, leading `0x00`, then 6
chars matching `^[A-Z0-9]{6}$`. Anything else falls through to avoid
false positives.

## Detection Significance

- A device matching this UUID is almost certainly part of the same fleet
  (UUID is too vendor-specific to collide). If you re-encounter one,
  check whether you're near refrigerated retail equipment.

## Parsing Strategy

1. Match if service-data carries the full 128-bit UUID
2. Strict body shape: `00 + [A-Z0-9]{6}` — reject anything else
3. Extract the 6-char `sensor_id`
4. Tag `device_class="sensor"`, `beacon_type="cold_chain_56d6"`

## Identity Hashing

`sensor_id` looks stable per-device (same store visit produced 3 distinct
IDs, no MAC was recorded with these captures), so identity uses it
instead of the MAC:

```
identifier = SHA256("cold_chain_56d6:{sensor_id}")[:16]
```

This survives MAC rotation and groups all sightings of the same physical
sensor.

## What We Cannot Parse

- Temperature, humidity, or any actual sensor reading
- Battery / firmware
- Vendor name or product line — *we don't know who makes these yet*

## Open Questions

- **Who is the vendor?** Web search on the UUID literal hasn't surfaced
  a hit. Anyone recognizing the 6-char sensor-ID format or the UUID
  shape, please open an issue or update this doc.
- Does the device respond to BLE scan-requests with extended data?
- Does GATT connect surface temperature characteristics?

## References

- Source: live capture in a small bespoke supermarket near refrigerated
  shelves (NRF Connect, 2026-04-26)
