# Xirgo / Sensata XT6300 ELD (HarpBT)

## Overview

Xirgo Technologies (acquired by Sensata in 2021) ships the XT6300
IB1 hardware revision — internal codename **"Harp"** — as a
commercial-vehicle telematics gateway and FMCSA-compliant
Electronic Logging Device (ELD). Production models in this family:
**XT6372, XT6383, XT6388**. Trucks driving under FMCSA Hours-of-
Service rules carry one of these in the cab; in passive BLE scans
they show up near highways, truck stops, loading docks, and any
commercial-fleet vehicle the user happens to be near.

The BLE advertisement is identification-only. Engine telemetry,
HOS clock, and driver authentication data are exchanged via the
documented GATT services and require a paired session — typically
with the driver's authenticated fleet app.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `^HarpBT\d{9}$` | 9-digit unit serial (opaque, treated as unique device id per Xirgo / Blue2thprinting docs) |
| Service UUID (Engine) | `1B19B844-038F-11E5-8418-1697F925EC7B` | Confirmed via Xirgo's own gitlab docs |

Either signal alone is sufficient to claim the device; both together
are unambiguous.

### Sibling services (not used for routing, but confirm the family)

| Service | UUID |
|---------|------|
| Engine | `1B19B844-038F-11E5-8418-1697F925EC7B` |
| Timer | `1B19BB5A-038F-11E5-8418-1697F925EC7B` |
| HOS | `A59611BA-78B7-4FD2-96FB-9B0F66D2311E` |

The UUIDv1 timestamp embedded in the first two (`038F-11E5`)
decodes to roughly 2015-05-19 — consistent with Xirgo minting the
UUID family at the start of the XT6300 product line.

## Local Name Decoding

```
"HarpBT230412586"
 └──┬─┘ └────┬────┘
    │        └── 9-digit unit serial (opaque per-device unique id)
    └── product codename + "BT" (BLE radio suffix)
```

The 9-digit suffix is treated as opaque — it is *not* a
manufacturing-date prefix (the Blue2thprinting metadata flags it as
a unique id, and another sighting in the wild was `HarpBT195007401`
which doesn't fit a YYMM date prefix). Surface verbatim as `serial`.

## Wire Format

No manufacturer data, no service data in the advertisement. The
GATT control surface (post-connect) carries the actual engine and
HOS data; that protocol is documented at xirgo.gitlab.io but
requires a paired session — out of scope for a passive scanner.

## Identity Hashing

```
identifier_hash = SHA256(serial)[:16]      # preferred
identifier_hash = SHA256(mac_address)[:16] # fallback when name absent
```

The 9-digit serial is stable per physical device and survives BLE
MAC rotation — right key for cross-session identity.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | UUID + name | Sensata (Xirgo Technologies) |
| Product family | UUID | XT6300 IB1 "Harp" |
| Unit serial | local name | 9-digit opaque id |

## What Requires GATT Connection

- Engine state (RPM, speed, ignition)
- HOS (Hours-of-Service) clock
- Driver-authentication tokens
- Fault codes / DTCs
- Trip event log

## Context Hint for the UI

This is a commercial-fleet device — useful neighborhood-context
signal. Seeing several `HarpBT` units clustered usually means you
are at or near a truck stop, freight terminal, or fleet yard.

## References

- [Xirgo XT6300 IB1 Harp BLE — Engine / Timer / HOS Services](https://xirgo.gitlab.io/telematics/reanimate/antora/XT6300/IB1/Harp/Bluetooth_BLE/ELD_Services/User_Services_(HOS,_Engine,_and_Timer).html) — official UUID confirmation
- [Xirgo XT6300 IB1 Harp Manual Version](https://xirgo.gitlab.io/telematics/reanimate/antora/XT6300/IB1/Harp/Manual_Version.html) — confirms "Harp" codename + XT6372/XT6383/XT6388 model list
- [darkmentorllc/Blue2thprinting Metadata_v2.json](https://github.com/darkmentorllc/Blue2thprinting/blob/main/Analysis/metadata/Metadata_v2.json) — `^HarpBT[0-9]{9}` regex mapped to "Sensata ELD, XT6300 or XT2400"; serial flagged as unique id
- [IanMercer/pi-sniffer heuristic-names.c](https://github.com/IanMercer/pi-sniffer/blob/master/src/bluetooth/heuristic-names.c) — independent third party detecting `HarpBT*` in BLE scans
