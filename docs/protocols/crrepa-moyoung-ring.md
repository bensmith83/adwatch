# CRRepa / MoYoung "Da Rings" White-Label Rings and Bands

## Overview

The **CRRepa BLE SDK** (`com.crrepa.ble.*`) is the OEM SDK behind the MoYoung
"Da Fit" / "Da Rings" white-label band and ring fleet. The analysed app is
`com.moyoung.ring` (Da Rings). The SDK discovers devices **entirely by parsing
two service-data AD elements** (AD type `0x16`):

- `0xFDDA` **device-info** — firmware-type string, MCU platform, chip ID and a
  16-bit capability bitmask, all cleartext and essentially static per device.
- `0xFDD0` **setting-info** — dial/shell colour, size, type and a visibility flag.

There is no manufacturer data, no name filter, and no live health telemetry in
the advertisement. The format is fleet-wide across devices embedding
`com.crrepa.ble`, not specific to this app.

Related fleets: [oudmon-qring-ring.md](oudmon-qring-ring.md) (`0xFEE7` + model-code
name), [zh-berry-ring.md](zh-berry-ring.md) (`0xFE78` service data). Note that
adwatch's [zl02pro-dafit.md](zl02pro-dafit.md) documents a *different* "Da Fit"
smartwatch profile (`FEEA` service data + variant magic); the report does not
connect the two, so do not assume the `FDDA` parser applies to those watches.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service data UUID | `0xFDDA` (on-air `DA FD`) | SIG member range (`0xFDxx`); assignee not in adwatch's UUID table. UUID alone is not unique — the SDK gates on the `DA FD` magic + length. |
| Service data UUID | `0xFDD0` (on-air `D0 FD`) | Setting-info record |
| Company ID | — | No manufacturer data |
| Local name | — | Not used for discovery; firmware-dependent |

The SDK uses the deprecated `BluetoothAdapter.startLeScan` with **no ScanFilter**
and walks the raw AD TLV stream in software (`CRPScanRecordParser.parseScanRecord`),
acting only on AD type `0x16`.

> **Offset convention.** Offsets below are into the service-data value **as
> adwatch receives it** (UUID stripped). The report's tables index the raw AD
> value with the 2-byte UUID at 0–1; subtract 2 from the report's offsets to get
> these.

### `0xFDDA` device-info (≥ 6 payload bytes; capability needs ≥ 7)

| Offset | Field | Size | Decode |
|--------|-------|------|--------|
| 0–2 | firmwareType | 3 | ASCII, leading `"0"` stripped |
| 3 | MCU platform | 1 | enum, table below |
| 4 | chipId | 1 | platform-keyed enum, table below |
| 5–6 | capability bitmask | 2 | uint16 **LE**; only decoded when present |

MCU platform: `0` none, `1` Nordic, `2` Huntersun, `3` Realtek, `4` Goodix,
`6` Jieli, `7` Bluetrum (`5` unmapped → none).

chipId by platform: Nordic `1` nRF51822, `2` nRF52832, `3` nRF52810, `4` nRF52840;
Huntersun `1` HS6620D_A3, `2` HS6620D_A4, `3` HS6621; Realtek `1` RTL8762C,
`2` RTL8762D; Goodix `1` GR5515.

Capability bits (low byte only defined): `0x01` touch, `0x02` display, `0x04`
motor, `0x08` LED, `0x10` "tappy", `0x20` record, `0x40` WiFi, `0x80` storage.

### `0xFDD0` setting-info (≥ 4 payload bytes)

| Offset | Field | Size | Decode |
|--------|-------|------|--------|
| 0 | colour | 1 | uint8 index |
| 1 | size | 1 | uint8 index |
| 2 | type | 1 | int8 product type/variant |
| 3 | visible | 1 | bool, `> 0` |

## What We Can Parse from Advertisements

firmwareType, MCU platform, chip part, capability flags (form-factor inference:
display/motor/recorder/WiFi/storage), colour/size/type/visibility.

## What Requires GATT

HR / SpO2 / HRV / sleep / steps / temperature and control — over the `0xFDDA`
GATT service (`fdd1` notify / `fdd2` write), which the report describes as
plaintext and unauthenticated.

## Identity Hashing

No MAC or serial in the advert. Suggested:
`SHA256("crrepa:{mac}:{firmwareType}:{platform}:{chipId}")[:16]` — the silicon
fingerprint is static but shared by every unit of the same SKU, so the MAC is
the per-unit component.

## Detection Significance

- Persistent silicon + firmware fingerprint useful for targeting known-vulnerable
  firmware.
- The capability bitmask is passive reconnaissance (does it have a mic/recorder?
  WiFi? storage?).
- Rings advertise continuously while unconnected.

## adwatch Status

No plugin matches `0xFDDA`/`0xFDD0`. A future plugin would match service-data
`0xFDDA` (and/or `0xFDD0`), require the length gates above, and decode the tables.

## References

- apk-ble-hunting `reports/moyoung-ring_passive.md` (and `reports/moyoung-ring.md`)
- Code cited by the report: `com.crrepa.ble.scan.CRPScanRecordParser`
  (`:27-32` magic checks, `:44` AD-type gate, `:53-72` field decode),
  `com.crrepa.ble.scan.bean.CRPScanRecordInfo` (enum tables), `o1/a.java:83`
  (`startLeScan`)
