# WHOOP Fitness Strap

## Overview

WHOOP is a continuously-worn fitness / recovery strap (subscription
model, no on-device screen). Generations 3, 4, and the 2024 MG strap
all advertise over BLE so the WHOOP mobile app can pair to them and
sync workout / sleep data several times per day.

When the strap is broadcasting actively (a workout is in progress, or
the device just woke up), it includes the BLE Heart Rate service
(`0x180D`) so any standard BLE HR client (Apple Watch, Garmin head
unit, Peloton, Zwift, …) can subscribe to live BPM. When idle, the
strap still emits a discovery beacon with just the local name.

adwatch attributes the strap from the local name and exposes a stable
per-device identifier (the serial visible in the name) so multiple
sightings group cleanly even after BLE-MAC rotation.

## Supported Models

| Generation | Serial prefix (observed) | Notes |
|------------|--------------------------|-------|
| WHOOP 3    | `3A…`, `3B…`             | Original 3.0 strap |
| WHOOP 4    | `4A…`, `4B…`, `4C…`, `4D…`, `4M…` | Wireless-charge generation |
| WHOOP 5    | `5A…`, `5B…`, `5M…`      | 2024 hardware refresh |
| WHOOP MG   | `MG…`                    | Medical-grade strap (ECG / blood-pressure pilot) |

Serial alphabet is `[A-Z0-9]`, length 6–12 characters in field
captures. The first character (or first two for MG) encodes the
hardware generation.

## BLE Advertisement Format

### Identification

```
local_name: "WHOOP <serial>"
            └────┬───┘ └─┬──┘
                 │       └── 6-12 char alphanumeric serial
                 └────────── literal prefix
service_uuids:   [180D]      ← BLE Heart Rate service, present when active
manufacturer_data: (none)
service_data:      (none)
```

Regex: `^WHOOP ([A-Z0-9]{6,12})$`

The parser does NOT require the Heart Rate UUID to be advertised
(WHOOP suppresses it when the strap is in low-power idle), but
records its presence in `heart_rate_service=yes|no` for downstream
context.

### Why no manufacturer data

WHOOP intentionally minimizes the advertisement to extend battery
life. All real telemetry — strain, recovery score, sleep stages,
HRV — is computed on the strap and synced over an authenticated
GATT session triggered by the WHOOP app. Live heart-rate is the
only data ever exposed over the air, and it requires an active GATT
subscription to the Heart Rate characteristic.

## Identity Hashing

```
identifier_hash = SHA256("whoop:{serial}")[:16]
```

The serial in the name is the long-term device identity. BLE MAC
rotates frequently (every few minutes when worn). Using the serial as
the identity key collapses all rotated sightings into one record per
physical strap.

## What We Cannot Parse Without GATT

- Battery level (requires reading 0x180F / battery characteristic)
- Live heart-rate BPM (requires Heart Rate notification subscription)
- Workout / strain / recovery / sleep telemetry (proprietary,
  authenticated GATT)
- Firmware version

## Privacy Considerations

A WHOOP serial visible in the local name is **persistent and globally
unique**. Anyone within ~30 m can correlate the wearer across sites by
that string alone. This is a useful detection signal for adwatch but
worth flagging in privacy / threat-model write-ups.

## References

- WHOOP product line: https://www.whoop.com/
- WHOOP 4 BLE GATT reverse-engineering notes (community):
  https://github.com/jasonadams/WhoopBLE
- Bluetooth SIG Heart Rate service (0x180D): https://www.bluetooth.com/specifications/specs/heart-rate-service-1-0/
