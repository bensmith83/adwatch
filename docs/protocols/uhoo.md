# uHoo Air-Quality Monitors (Aura / Home / Caeli)

## Overview

uHoo "9-in-1" indoor air-quality monitors are **WiFi** devices. BLE exists
only to **onboard the sensor onto WiFi** via the Nordic Wi-Fi Provisioning
Service (app `com.uhooair`). No air-quality reading (CO2, VOC, PM,
temperature, humidity, CO, NO2, ozone, pressure) is ever broadcast over BLE —
readings go WiFi → uHoo cloud. Honest-negative / contrast case.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | *(none)* | No manufacturer data. |
| Service UUID (128-bit) | `14387800-130c-49e7-b877-2881c89cb258` | Nordic Wi-Fi Provisioning Service — setup mode only; **generic Nordic**, not uHoo-specific. |
| Local name | `uHoo_<suffix>` | Upper-cased device-identifier suffix; models `uHoo Aura` / `uHoo Home` / `uHoo Caeli`. |

Visible essentially only while the unit is in WiFi-provisioning / setup mode;
once provisioned it typically stops advertising for provisioning.

## What We Can Parse from Advertisements

| Field | Source |
|-------|--------|
| uHoo device in setup mode | `uHoo_` name and/or `14387800-…` UUID |
| Per-device suffix | name tail |

## What Requires GATT Connection

WiFi provisioning only (SSID + password written to the provisioning Control
Point — encryption depends on Nordic provisioning mode; an active setup-time
concern, not passive). Sensor data is not on BLE at all.

## Identity Hashing

```
identifier = SHA256("uhoo:" + name_suffix)[:16]
```

## Detection Significance

Minimal: reveals a uHoo exists and is (transiently) being set up. No
occupancy/air-quality inference from BLE.

## adwatch Status

No plugin. Optional future presence/setup-mode plugin: name prefix `uHoo_`
(the `14387800-…` UUID alone should map to a generic "Nordic Wi-Fi
provisioning" label, not uHoo).

## References

- apk-ble-hunting `reports/uhooair_passive.md`
- App code cited: `yl/g.java` (provisioning UUIDs), `AuraDevice.java:563`, `zg/c.java:10-12` (names)
