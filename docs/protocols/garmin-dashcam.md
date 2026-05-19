# Garmin Dash Cam Plugin

## Overview

[Garmin's Dash Cam line](https://www.garmin.com/en-US/c/automotive/dash-cameras/) (DC 47, DC 57, DC 67W, DC 76, Dash Cam Mini 2, etc.) is a series of small in-car cameras that pair with the **Garmin Drive** smartphone app over BLE to download footage, set incident-detection sensitivity, and reconfigure recording profiles. Each unit advertises continuously so the app can re-pair without user intervention.

This parser surfaces the cam's model number and unit serial, both of which are encoded in the BLE local name.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0087` | Garmin International, Inc. (SIG). Shared with sport watches and the existing `GarminParser`. |
| Service UUID | `0xFE1F` | Garmin's SIG member service UUID. |
| Local name | `^DC\d{2,3}-\d{3,8}$` | E.g. `"DC47-14316"` (Dash Cam 47, unit 14316). |

The existing `GarminParser` covers the Forerunner / fenix / vivoactive / Edge / Instinct / Index / Lily / vivosmart / vivomove / HRM- sport-watch families on the same company ID. That parser explicitly rejects anything outside its sport-watch name regex, so this dash-cam parser does not conflict.

The Bluetooth SIG member-services registry lists `0xFE1F = Garmin International, Inc.` ([YAML mirror](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml)).

### Local Name Format

`DC<model digits>-<unit serial>`

- `DCxx` — the Dash Cam model number (e.g. `DC47` = Dash Cam 47, `DC67` = Dash Cam 67W).
- The trailing 3-8 digit number is the per-unit serial visible on the back of the cam.

Example: `"DC47-14316"` → model `DC47`, serial `14316`.

### Manufacturer Data

8 bytes after the company ID, e.g. `f4 0e 20 6d 12 6e 44 0a`. The structure is opaque to us — bytes vary across sightings but no per-byte semantics have been validated. We expose it as `payload_hex` for further investigation; it does **not** carry the identity (that comes from the local name).

## Detection Significance

- **Cars in parking lots / drive-throughs.** A dense cluster of DC-series advertisements is a strong signal that you're scanning in a busy parking lot or near a road — every Garmin-equipped vehicle in earshot will broadcast.
- **Stable serial enables tracking.** The local-name serial is a unique per-unit identifier that persists across MAC rotations. Garmin doesn't appear to rotate or salt it.

## What We Cannot Parse from Advertisements

- The actual cam status (recording / parked / incident-detected) — almost certainly only available via the GATT connection that the Garmin Drive app sets up.
- Footage download — that's a GATT-side bulk transfer.

## References

- [Garmin Dash Cam product line](https://www.garmin.com/en-US/c/automotive/dash-cameras/)
- [Bluetooth SIG member UUIDs (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
