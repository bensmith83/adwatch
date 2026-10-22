# Circular Ring 2 (Circularing)

## Overview

**Circular Ring 2** (`xyz.circular.circular`, Circularing / Paris) is an ECG
smart ring (FDA-cleared AFib, SpO2, sleep). The app is React Native + Hermes
with BLE via react-native-ble-plx, and advertisement decoding compiled into a Go
`libgojni.so` (`c2lib`). Not to be confused with BodiMetrics CIRCUL
(`com.circul.zg29`).

Two passive surfaces:

1. **Nordic UART Service UUID + a configurable "CR"-style local name**
   (MEDIUM confidence, from Hermes strings).
2. **Manufacturer data embedding the device MAC + a 7-byte serial**, in two
   fixed-length formats (layout resolved from the Go library; the **company ID is
   still unknown** — it is consumed in the JS layer).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` (NUS) | MEDIUM — "likely the advertised service UUID". Generic Nordic, never match alone (see [nordic-uart-service.md](nordic-uart-service.md)). |
| Service UUID | `0x1822` (SIG Pulse Oximeter) | Corroborator if co-advertised; vendor-agnostic |
| Local name | user-configurable "CR3"-style name | App has a `deviceNamePrefix` filter but the literal is runtime/config-dependent; Go label format `CR%04s%02dL%02s%02s%03s` |
| Company ID | **unknown** | Needs a live capture |

Two hardware generations (gen1/`N1`, gen2/`N2`): gen1 uses Dialog SUOTA
(`0xFEF5`) for OTA plus 9 custom 128-bit UUIDs (roles unresolved); gen2 uses
Nordic Secure DFU (`0xFE59`).

### Manufacturer data payload (after the 2-byte company ID)

Selected by `manufacturerDataLayout`; wrong lengths are rejected
(`bad manufacturer data length %d`).

| Format | Length | Selected when | Cut points |
|--------|--------|---------------|-----------|
| A | 17 | `data[7]` in 4..16 **and** `data[9] == 0x23` | `{6, 7, 8, 10, 17}` |
| B | 19 | otherwise (len ≥ 19) | `{8, 9, 10, 12, 19}` |

Format A field layout:

| Offset | Field | Size | Decode | Confidence |
|--------|-------|------|--------|-----------|
| 0–5 | MAC | 6 | raw bytes rendered `%02X`×6 | HIGH |
| 6 | colour / size code | 1 | mapped to name, fallback `UNKNOWN_%d` | MEDIUM |
| 7 | size / version code | 1 | discriminator, must be 4..16 | MEDIUM |
| 8–9 | battery % + charging | 2 | one byte each | MEDIUM |
| 10–16 | serial number | 7 | → SNU via `manufacturerSNUFromSN` | HIGH |

Format B's field split follows its cut points; the report does not give a
per-field table for it ("exact middle-byte field split" is listed as unresolved).

## What We Can Parse from Advertisements

Embedded MAC, serial/SNU, colour/size code, battery and charging (once the
company ID is known). Today, only NUS + optional `0x1822` + a `CR`-style name.

## What Requires GATT

All HR / ECG / SpO2 data streams over NUS (`6E400002` write, `6E400003`
notify) and is processed on-phone by `c2lib`.

## Identity Hashing

Once the record can be matched: `SHA256("circular:{embedded_mac}")[:16]` — the
embedded MAC/SNU survives link-layer address rotation. Until then, fall back to
BD_ADDR.

## Detection Significance

- **MAC + serial in manufacturer data = persistent globally-unique identifier**
  (the report's headline privacy concern).
- NUS + Pulse-Oximeter marks the device as a health/biosignal wearable.
- Go command set includes `CMD_WRITE_CID` / `CMD_READ_ADDR` — address/ID may be
  app-writable (not passively observable).

## adwatch Status

No plugin. Blocked on the company ID from a live capture; then match on CID +
length 17/19 and decode as above. Do not gate on NUS or the name alone.

## References

- apk-ble-hunting `reports/circular-circular_passive.md`,
  `reports/circular-circular_native.md` (Stage 6c layout recovery),
  `reports/circular-circular.md`
- Code cited by the report: `libgojni.so` symbols `ecg-ring/c2lib.manufacturerDataLayout`,
  `manufacturerMac`, `manufacturerSNUFromSN`, `decodeManufacturerDataString`
