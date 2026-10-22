# Atmotube PRO / PLUS (Portable Air-Quality Monitor)

## Overview

Atmotube PRO and PLUS (Atmotech) are wearable air-quality monitors. They are
a **continuous telemetry beacon**: the companion app (`com.atmotube.app`)
decodes VOC, temperature, humidity, pressure, battery and status — and on
PRO, PM1/PM2.5/PM10 + firmware version — straight from the advertisement in a
background scan job, without connecting. Strong passive-plugin candidate.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | exactly `ATMOTUBE` | The app's only `ScanFilter`. Test firmware: `atmotube` / `atmotest3`. Carries no serial. |
| Service UUID (128-bit) — PLUS (HW3) | `db450001-8e9a-4818-add7-6ed94a328ab3` | Selects the PLUS decode path |
| Service UUID (128-bit) — PRO (HW4) | `db450001-8e9a-4818-add7-6ed94a328ab4` | Selects the PRO decode path |
| Company ID | *(none read)* | The app never calls `getManufacturerSpecificData`; the report says telemetry rides in service data + scan response. |

Use an **active scan** — PM and firmware are in the scan response.

### Telemetry layout

**Offsets are absolute into Android `ScanRecord.getBytes()`** (advert PDU +
scan response concatenated), exactly as the app reads them. Multi-byte
integers are **big-endian**.

#### Primary advertisement (PLUS and PRO)

| Offset | Field | Size | Decode | Unit |
|---|---|---|---|---|
| 7–8 | VOC | 2 | uint16 BE ÷ 1000 | ppm |
| 9–10 | Device CRC / id | 2 | uint16 BE | — |
| 11 | Humidity | 1 | uint8, clamp ≤ 100 | %RH |
| 12 | Temperature | 1 | int8 (signed) | °C |
| 13–16 | Pressure | 4 | uint32 BE ÷ 100 | hPa |
| 17 | Status bitfield | 1 | see below | — |
| 18 | Battery | 1 | uint8 | % |

#### Scan response — PRO (`…ab4`)

| Offset | Field | Size | Decode | Unit |
|---|---|---|---|---|
| 51–52 | PM1 | 2 | uint16 BE | µg/m³ |
| 53–54 | PM2.5 | 2 | uint16 BE | µg/m³ |
| 55–56 | PM10 | 2 | uint16 BE | µg/m³ |
| 57–59 | Firmware version | 3 | hex string | — |

`0xFFFF` in a PM field = sensor off.

#### Scan response — PLUS (`…ab3`)

| Offset | Field | Size | Decode |
|---|---|---|---|
| 51–52 | ADC (raw) | 2 | uint16 BE |
| 53–54 | Battery voltage | 2 | uint16 BE ÷ 100 → V |
| 57–59 | Firmware version | 3 | hex string |

PLUS has no PM sensor.

#### Status bitfield (offset 17)

| Bit | Meaning |
|---|---|
| 0 (`0x01`) | PM sensor ON |
| 1 (`0x02`) | [fw 73/74] charging / external power (batt V & error zeroed when set) |
| 2 (`0x04`) | [fw 73/74] bonded |
| 3 (`0x08`) | Charging |
| 4 (`0x10`) | Charging timeout |
| 5 (`0x20`) | **0 = activated** |
| 6 (`0x40`) | **0 = calibrating** (VOC warm-up) |
| 7 (`0x80`) | reserved / flag `c` |
| bits 0–2 + 1 | battery level 1–8 (older, non-73/74 firmware only) |

Firmware generation from fw-version hex prefix: `70…` HW1, `72…` HW2,
`73…` PLUS, `74…` PRO.

#### Re-anchoring to AD structures (adwatch note — unverified)

The report itself warns the offsets must be re-anchored to AD structures and
validated against a live capture. Offset arithmetic (ours, not the report's):
with a 3-byte Flags AD at 0–2, an AD header at 3–4 and **2 bytes at 5–6**
before VOC at 7, the primary-advert telemetry element has a 2-byte prefix —
consistent with a 16-bit service-data UUID or a 2-byte company ID, but **not**
with a 128-bit service-data UUID (which would push VOC past offset 20). The
128-bit `db450001-…` UUID therefore most likely sits in the scan response
(e.g. a 16-byte UUID-list AD at 31–48, then an AD whose payload starts at
51). Which AD types carry the payloads is unresolved; a plugin should be
built from a real capture, not from these absolute offsets.

#### Legacy HW1/HW2

Older units embed an `ATMOTUBE` / `ATMOTEST` magic header in the advert and
fields are read at header-relative offsets (`y7.d`, `y7.java:60-123`).

## What We Can Parse from Advertisements

VOC, temperature, humidity, pressure, battery, status flags (calibrating,
charging, PM on, activated/bonded), 2-byte device CRC, and on PRO PM1/PM2.5/
PM10 + firmware version.

## What Requires GATT Connection

Nothing needed for live readings; history/config is GATT (out of scope here).

## Identity Hashing

No serial in the advert. Combine the non-rotating BD_ADDR with the 2-byte CRC:

```
identifier = SHA256(f"atmotube:{mac}:{device_crc:04x}")[:16]
```

## Detection Significance

- **Environmental surveillance without pairing:** logging a wearer's VOC /
  PM / temp / humidity reveals occupancy, cooking, smoking/vaping spikes,
  ventilation habits — more sensitive than a presence beacon.
- Fixed name + CRC + firmware + likely static MAC → per-device tracking of a
  worn device.
- Payload is plaintext and unauthenticated (spoofable).

## adwatch Status

No plugin (`grep -ri atmotube src/` empty). Future plugin: match name
`ATMOTUBE` or the two `db450001-…` UUIDs; decode the tables above once
re-anchored to a live capture.

## References

- apk-ble-hunting `reports/atmotube-app_passive.md`
- App code cited: `defpackage/y7.java:125-232` (parser `y7.e`), `:185-189` (generation select), `:190-224` (offsets), `:17-22`/`:60-123` (legacy); `com/atmotube/ble/UpdateDataHolder.java:103-138,415-425`; `defpackage/t7.java` (status bits); `com/atmotube/app/service/a.java:183` (scan filter); `defpackage/s7.java` (UUID families)
- Public Atmotech BLE advertising spec and the `atmotuber` Dart library (cross-reference cited by the report)
