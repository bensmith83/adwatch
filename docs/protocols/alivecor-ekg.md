# AliveCor KardiaMobile EKG Plugin

## Overview

AliveCor KardiaMobile is a personal EKG/ECG monitor that pairs with a smartphone via BLE. It continuously advertises over BLE for device discovery. These are extremely common in households with health-conscious users.

## BLE Advertisement Format

### Identification

AliveCor EKG devices can be identified by:

1. **Local Name Pattern**: `EKG-*` (e.g., `EKG-99-23-4c`)
2. **Service UUID**: `021a9004-0382-4aea-bff4-6b3f1c5adfb4` (custom AliveCor service)

Best match strategy: `local_name_pattern=r"^EKG-"` and/or `service_uuid="021a9004-0382-4aea-bff4-6b3f1c5adfb4"`.

### Advertisement Data

- Local name contains device identifier bytes (hex values separated by dashes)
- No manufacturer data observed — identification is via service UUID and local name
- No service data payload observed

### Parser Scope (Passive Only)

The parser extracts:
- Device identifier from local_name (the hex portion after "EKG-")
- Presence detection (device is powered on and advertising)

Note: Actual EKG readings require an active GATT connection via the Kardia app. The parser provides device identification and presence.

## Observed in DB

- Local name: `EKG-99-23-4c`
- Service UUID: `021a9004-0382-4aea-bff4-6b3f1c5adfb4`
- No manufacturer_data
- No service_data
- 959k+ sightings (very active advertiser)

## References

- [AliveCor KardiaMobile](https://www.alivecor.com/)
- [Kardia BLE analysis](https://github.com/nicpottier/kardia-python)
