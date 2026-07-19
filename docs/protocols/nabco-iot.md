# Nabco Remote Connect (Automatic Door BLE Controller)

## Overview

**Nabco Entrances Inc.** (Muskego, WI) — a subsidiary of **Nabtesco
Corporation** (Japan) — makes commercial-grade automatic pedestrian
doors, ICU/sliding hospital doors, and gate operators. Their
**Nabco Remote Connect** product is a jamb-mounted BLE smart switch
paired with the **NABCO Connect** iOS/Android app, released alongside
the NABCO SWING non-handed swing-door operator in September 2023. The
controller lets users open/close doors and schedule day/night modes
from a phone; remote dashboards track cycle counts, fault codes, and
motor health.

The advertisement broadcasts the unit's serial in the local name plus a
vendor-defined GATT service. Live telemetry (cycle count, fault codes,
motor current) is exposed over a GATT connection, not in the advertisement.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `Nabco IOT-<16-hex>n` | e.g. `Nabco IOT-9A23ACB4CF386821n`. The 16-hex block is a per-unit serial; trailing `n` is fixed |
| Service UUID | `94E06D56-DAAA-4B2B-B9D1-7B1559AE7300` | Nabco vendor-defined GATT service (not registered in BT SIG `member_uuids.yaml`) |
| Service UUID | `1805` | Standard SIG **Current Time Service** — door controller exposes a clock characteristic so the central can sync timestamps for cycle logging |
| Manufacturer data | (absent in observed captures) | — |
| Service data | (absent in observed captures) | — |
| Address type | `random` | rotating private address |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Nabco Entrances` |
| Parent company | hard-coded | `Nabtesco Corporation` (Japan) |
| Product | hard-coded | `Nabco Remote Connect` (jamb-mounted BLE smart switch) |
| Model name | hard-coded | `Nabco IOT` (the literal localName prefix) |
| Device class | hard-coded | `access_control` |
| Unit serial | localName | 16 hex chars between `IOT-` and trailing `n` |
| Has Current Time Service | `serviceUUIDs` | Boolean — central could read `2A2B` to confirm |
| Vendor service UUID | hard-coded | `94E06D56-DAAA-4B2B-B9D1-7B1559AE7300` |

### What We Cannot Parse from the Advertisement

- Door state (open / closed / opening / closing / fault).
- Cycle / activation count.
- Fault codes or motor health.
- Firmware version.

All of those live under the `94E06D56` GATT service and need a connection +
the vendor's characteristic map. None of that has been publicly documented;
the parser deliberately stops at presence + serial.

## Stable Identity

The 16-hex serial in the local name is per-unit and survives MAC rotation
(observed across multiple sightings in the same capture window), so it
makes a better stable key than the rotating private MAC.

```
stable_key = nabco_iot:<serial-hex-lowercased>
```

If for some reason the serial is missing (corrupted name), fall back to
`nabco_iot:mac:<mac>`.

## Detection Significance

- Indicates a commercial / institutional venue: hospitals, airports,
  retail entrances, transit stations, parking-garage gates. Nabco IOT
  is sold through facilities-management channels, not consumer retail.
- Two distinct units at the same site (export 17 captured exactly two)
  usually means a vestibule pair — main entrance + inner door operating
  as an airlock — or a paired ingress / egress at a parking gate.
- Random-address with a vendor-stable local-name serial is a recurring
  industrial-IoT shape (see also `HoneywellIH40Parser` for the
  warehouse-scanner analogue).

## References

- Nabco Entrances product line — <https://www.nabcoentrances.com/>
- Nabco Remote Connect product page — <https://www.nabcoentrances.com/product/nabco-remote-connect/>
- Nabco — Bluetooth-related releases — <https://www.nabcoentrances.com/tag/bluetooth/>
- Introducing the NABCO SWING (Sept 2023, paired with Remote Connect) — <https://www.nabcoentrances.com/introducing-the-nabco-swing/>
- NABCO Connect on the App Store — <https://apps.apple.com/us/app/nabco-connect/id6446406500>
- Nabco / Nabtesco parent-company page — <https://www.nabcoentrances.com/our-company/>
- FCC grantee O82 (NABCO Entrances) — <https://fccid.io/O82-ACUMOTION>
- Bluetooth Core Specification 5.4, Vol 3 Part G — Current Time Service
  (UUID `0x1805`, characteristic `Current Time 0x2A2B`)
- BT SIG `member_uuids.yaml` (no entry for `94E06D56-…` — vendor-defined,
  not registered)
- Export 17 capture: `research/adwatch_export 17.json`, two units, 342
  combined sightings on 2026-06-03
