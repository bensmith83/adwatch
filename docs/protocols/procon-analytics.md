# Procon Analytics (Elo GPS / Arrow / MyCar Telematics)

## Overview

**Procon Analytics, LLC** is a US-based automotive-telematics OEM.
They sell aftermarket GPS / OBD-II tracking dongles into the
new-car-dealer channel under several brands:

- **Elo GPS** — consumer-facing stolen-vehicle-recovery and
  driver-monitoring product. The hardware is an OBD-II pass-through
  with cellular + Bluetooth + GPS.
- **MyCar** — remote-start companion module.
- **Oigo Telematics** — Latin America fleet line.
- **Arrow / ArrowQ** — internal product codenames seen in the
  advertisement local-name field, presumed to be a recent
  generation of the OBD-II dongle.

The dongle is permanently powered by the vehicle's OBD port, so it
advertises continuously when the car is on a charged battery, even
parked. In a single passive-scan capture we saw one unit sighting
with the local name `ArrowQ`.

The advertisement is identification-only — live telemetry (location,
fuel, battery, geofence state) goes out over cellular to Procon's
backend; the Bluetooth surface is used only by the Elo GPS app for
local pairing and OTA configuration via a paired GATT session.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0BD3` | "Procon Analytics, LLC" (Bluetooth SIG assigned) |
| Local name | `ArrowQ`, `Arrow`, `Elo`, or `MyCar` | Internal product codename or app-facing brand |

The CID alone is a strong signal — `0x0BD3` is single-vendor and
not commonly seen in consumer/IoT captures. The local name lets us
distinguish product lines within the Procon family.

## Wire Format (post-CID payload)

```
ArrowQ capture
mfr_hex = d3 0b | 08 62 09 40 67 19 69 15
          └─┬─┘ └───────────┬───────────┘
           CID          8-byte payload
```

Per-byte best-guess interpretation (unverified — single-unit capture):

| Offset | Bytes | Speculation |
|--------|-------|------------|
| 0      | `08`        | Frame type / version (`0x08`) |
| 1      | `62`        | Sub-type / state |
| 2–5    | `09 40 67 19` | Unit serial or session token (4 bytes) |
| 6–7    | `69 15`     | Counter / rolling-code-like sequence (the trailing two bytes are the most likely to vary across captures) |

We surface the full 8-byte payload verbatim as `payload_hex` and
flag the trailing 2 bytes as `counter_hex` for differential
analysis when we collect more samples.

## Identity Hashing

```
identifier_hash = SHA256("procon:{local_name}:{payload_bytes_0..5}")[:16]
identifier_hash = SHA256(mac_address)[:16]   # fallback if no payload
```

The dongle has a static BLE MAC (it lives in a parked car — no
real reason to rotate), but we prefer hashing on the first six
payload bytes because (a) they're plausibly the unit serial and
(b) iOS rotates MACs across pairings.

## Captured Examples

```
local_name="ArrowQ"   mfr=d3 0b 08 62 09 40 67 19 69 15   svc_uuid=(none)
```

One sighting in one capture; rare in residential scans because
the dongle is parked outside.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | CID | "Procon Analytics, LLC" |
| Product line | local name | "Arrow / ArrowQ / Elo / MyCar" |
| Device class | derived | `vehicle_telematics` |
| Payload hex | mfg bytes 2..N | Full payload preserved |
| Counter hex | mfg bytes (N-2)..N | Last 2 bytes (rolling) |

## What Requires GATT / Cellular Backend

- Live GPS position
- Fuel / battery telemetry
- Geofence breach notifications
- Stolen-vehicle-recovery status
- Remote start (MyCar)
- OTA firmware updates

All of the above happen out-of-band over Procon's cellular link;
the BLE GATT surface is only used by the Elo GPS / MyCar apps for
initial pairing.

## References

- Bluetooth SIG assigned numbers (company identifiers) —
  `0x0BD3 → Procon Analytics, LLC`
- Procon Analytics product page — proconanalytics.com (Elo GPS,
  MyCar, Oigo Telematics product family)
- Elo GPS OBD-II Reader Installation Guide
  (proconanalytics.com/wp-content/uploads/2019/05/EloGPS-Installation-Guide-4-25-19.pdf)
- PR Newswire (2017): "Procon Analytics Launches Suite of
  Connected Car Telematics Products" — confirms the connected-car
  / OBD-II form factor
