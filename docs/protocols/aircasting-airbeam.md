# HabitatMap AirBeam2 / AirBeam3 / AirBeam Mini

## Overview

AirBeam is HabitatMap's open-source wearable PM monitor used with the
**AirCasting** app (`pl.llp.aircasting`). It is **not a telemetry beacon**:
measurements (PM1/PM2.5/PM10, temperature, humidity) stream over a connected
link. A scanner can see presence + model name only.

- **AirBeam2** — **Bluetooth Classic** (RFCOMM/SPP); found by classic
  inquiry, likely invisible to a BLE-only scanner.
- **AirBeam3 / AirBeam Mini** — **BLE**, advertise a device name; data needs
  a GATT connection.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | *(none)* | No manufacturer data. |
| Service UUID | *(not a literal in the APK)* | AirBeam3 measurement service/char UUIDs are in the public AirCasting repo, not this build. |
| Local name (BLE) | `AirBeam3`, `AirBeam3-PM2…`, `AirBeam-mini` | Model string; optional `-PM2`-style suffix. |
| Local name (Classic) | `AirBeam2`, `AirBeam2-PM2…`, `AirBeam2:` | Classic inquiry only. |

No serial or MAC is embedded in the name.

## What We Can Parse from Advertisements

| Field | Source |
|-------|--------|
| Model (AirBeam3 / Mini) | name prefix |

## What Requires GATT Connection

- AirBeam3: subscribe to the measurement characteristic (UUID from the
  HabitatMap/AirCasting GitHub source).
- AirBeam2: RFCOMM CSV serial stream.
- Post-connect CSV line: `Index, UUID, Date, Time, Lat, Lon, F, C, K, RH, PM1, PM2.5, PM10`.
- Setup writes WiFi SSID/password + AirCasting auth token in the clear over
  the config channel (active-MITM concern, not passive).

## Identity Hashing

```
identifier = SHA256("airbeam:" + mac)[:16]
```

AirBeam3 BLE address rotation is unknown.

## Detection Significance

Low data leak, but AirBeam is worn/carried, so logging its address tracks the
**wearer's movements**.

## adwatch Status

No plugin. Future presence plugin: name prefix `AirBeam3` / `AirBeam-mini`.

## References

- apk-ble-hunting `reports/llp-aircasting_passive.md`
- App code cited: `BluetoothManagerDefault.java` (classic discovery), `AirBeam2Reader.java`, `HexMessagesBuilder.java`, `AB3CSVLineParameterHandler`
- HabitatMap/AirCasting (open source) for AirBeam3 service/characteristic UUIDs
