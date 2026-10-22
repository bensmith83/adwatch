# Löwenstein Medical prisma CPAP / Ventilators ("prisma APP")

## Overview

Löwenstein Medical Technology (ex-Weinmann) prisma SMART / SOFT / VENT /
TIVAN / JOYCE therapy devices connect over Bluetooth modules **WM 090 MW /
WM 110 MW** to the **prisma APP** (`com.lmt.sleeppatientapp`, React Native /
Hermes, `react-native-ble-plx`).

The modules are built on the **Telit/Stollmann Terminal I/O (TIO)** stack,
and discovery is purely by the advertised 16-bit TIO service `0xFEFB`. No
manufacturer data, no service data. Device identity and all therapy data are
behind GATT and an authenticated, cloud-brokered challenge-response (ECDSA
P-521 signed, CRC32-tagged payloads).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | *(none parsed)* | Löwenstein/Weinmann has no SIG CID; bundle has zero `manufacturerData` references. |
| Service UUID (16-bit) | `0xFEFB` (`0000fefb-0000-1000-8000-00805f9b34fb`) | Telit/Stollmann Terminal I/O — **shared across many unrelated vendors**. AD vs scan response unconfirmed. |
| Local name (confirmatory) | contains `prisma`, or `WM 090` / `WM 100` / `WM 110` / `WM 120` | Present in the bundle as display/identity strings, **not** a scan filter; whether they are on-air is a live-capture TODO. |

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Telit TIO module present | `0xFEFB` | Not Löwenstein-specific alone |
| Löwenstein prisma (likely) | `0xFEFB` + `prisma` / `WM 0xx` name | Raise confidence only with the name |

The serial is **not** in the advertisement — it is a GATT read of DIS
`0x180A` → `0x2A25` (firmware `0x2A26`); the UI composes
`"{{deviceName}}. SN: {{deviceSerialNumber}}"` from the connected device.

## What Requires GATT Connection

- `info_get` / `state_get` / `therapy_get` / `humidifier_get` /
  `lockstate_get` / `softstart` / `durations_set` … over the TIO credit-flow
  serial pipe, under a 6-step cloud-brokered cert/challenge handshake.

## Interaction with existing adwatch plugin

`src/adwatch/plugins/telit_terminal_io.py` (doc: PARI SpiroSense origin)
already registers on service UUID `0000fefb-…` and CID `0x008F`. A prisma
advertising `0xFEFB` would therefore surface as a generic **Telit TIO**
device. The Löwenstein report does not mention the TIO `0x008F` /
`09 B0` manufacturer-data marker that plugin decodes, so it is unknown
whether prisma modules emit it. Gap: the plugin does not label `prisma` /
`WM 0xx`-named TIO adverts as a medical CPAP/ventilator.

## Identity Hashing

```
identifier = SHA256("lowenstein_prisma:" + mac)[:16]
```

(MAC is the only handle; no rotating-ID scheme asserted by the app.)

## Detection Significance

- `0xFEFB` + `prisma`/`WM 0xx` name identifies a CPAP/ventilator user —
  respiratory/sleep-disorder medical inference.
- Do **not** label `0xFEFB`-only adverts as medical.

## References

- apk-ble-hunting `reports/lmt-sleeppatientapp_passive.md` (Stage 4: `reports/lmt-sleeppatientapp.md`)
- Hermes bundle offsets cited: `0000fefb-…` @2555968, `startDeviceScan` @1838908, `serviceUUIDs` @2152984, `0x2A25` @1466972, `0x2A26` @1469077
- adwatch: `src/adwatch/plugins/telit_terminal_io.py`
