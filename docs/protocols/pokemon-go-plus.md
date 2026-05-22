# Pokemon GO Plus BLE Protocol

## Overview

The **Pokemon GO Plus** (original, 2016 — FCC ID **BKEPTC-001**, retail SKU
**D 25012** / PTC-001) is a Nintendo gaming accessory for Pokemon GO. It
advertises via BLE using Nintendo's SIG-assigned company ID `0x0553` while
game-connected, but on the **iOS pairing-mode** path it advertises with an
unregistered pseudo-CID `0xA00C` and the Dialog Semiconductor SUOTA service
UUID `21C50462`. The radio inside is a **Dialog Semiconductor DA14580**.

## Identifiers

- **Canonical company ID:** `0x0553` (Nintendo Co., Ltd.) — used while
  game-connected
- **iOS-observed pseudo-CID:** `0xA00C` (wire bytes `0c a0`; unregistered
  with the SIG) — used in pairing / SUOTA mode
- **iOS-observed reverse-byte variant:** `0x0CA0` (wire bytes `a0 0c`) —
  observed on some firmware revisions
- **Pairing service UUID:** `21C50462` (short form of
  `21c50462-67cb-63a3-5c4c-82b5b9939aef`, the Dialog Semi SUOTA family
  UUID)
- **Local name:** `Pokemon GO Plus`
- **Device class:** `gaming_accessory`
- **Retail SKU embedded in payload:** `D 25012` (Nintendo's internal label
  for the FCC-ID BKEPTC-001 retail unit)

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID (canonical) | `0x0553` | Nintendo, SIG-assigned. Game-connected mode. |
| Company ID (iOS-observed) | `0xA00C` / `0x0CA0` | Unregistered pseudo-CIDs surfaced by CoreBluetooth during pairing mode. |
| Service-data UUID | `21C50462` | Dialog Semi SUOTA family UUID (`21c50462-67cb-63a3-5c4c-82b5b9939aef`). Present on pairing-mode sightings. |
| Local name | `Pokemon GO Plus` | Case-sensitive. Required for all match paths. |

### Canonical (game-connected) manufacturer data — 17 bytes

```
53 05 01 ae de 00 f0 be 00 00 00 00 00 00 00 00 02
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0-1 | 2 | `53 05` | Company ID 0x0553 (Nintendo, little-endian) |
| 2 | 1 | `01` | Protocol version |
| 3-4 | 2 | `ae de` | Device ID |
| 5-16 | 12 | Varies | Reserved / state bytes |

### iOS-observed pairing-mode manufacturer data — 17 bytes

```
0c a0 44 20 32 35 30 31 32 76 1b 16 e9 b6 98 00 00
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0-1 | 2 | `0c a0` | LE pseudo-CID `0xA00C` (unregistered) |
| 2-8 | 7 | `44 20 32 35 30 31 32` | ASCII `"D 25012"` (retail SKU label) |
| 9 | 1 | `76` / `42` | Varies per emitter — likely per-unit rolling identifier |
| 10-16 | 7 | `1b 16 e9 b6 98 00 00` | Fixed tail |

### iOS-observed CID quirk

When the original Pokemon GO Plus is in iOS pairing mode (i.e. not yet
bound to a logged-in Pokemon GO session on a phone), CoreBluetooth surfaces
the device with an **unregistered pseudo-CID `0xA00C`** instead of
Nintendo's SIG-assigned `0x0553`. This is NOT a simple byte-order quirk of
the canonical CID — the wire bytes are entirely different (`0c a0` vs
`53 05`), so the device firmware genuinely emits a different company ID on
this code path. Working theory: the pairing/SUOTA firmware path on the
DA14580 SDK inherits Dialog Semi's example advertisement defaults (which
include the `21c50462-...` SUOTA service UUID and a vendor-magic
unregistered CID) rather than overriding them with Nintendo's SIG ID.

A small number of captures present the same payload with the company-ID
byte pair reversed (`a0 0c` → UInt16 LE `0x0CA0`). The parser accepts both
forms when paired with the `"Pokemon GO Plus"` local name.

### Name-only fallback

Some sightings carry no manufacturer data at all but still expose
`localName = "Pokemon GO Plus"` plus the `21C50462` service-data UUID. The
parser accepts this combination as a positive match. Bare `"Pokemon GO
Plus"` with no supporting service UUID is rejected — the name string is
too easy to spoof on its own.

### What we can parse from advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | company_id or local_name + service UUID | Original 2016 Pokemon GO Plus nearby |
| `cid_encoding` | match path | `canonical` (0x0553), `ios_observed_quirk` (0xA00C / 0x0CA0), `name_with_service_uuid` (name+UUID fallback) |
| `device_sku` | manufacturer payload bytes 0..6 (ASCII) | `"D 25012"` for the FCC-ID BKEPTC-001 retail unit |
| `pairing_service_uuid` | service data keys | `"21C50462"` when present |
| `protocol_version`, `device_id_hex` | canonical-CID payload | Game-connected mode only |

### What we cannot parse (requires GATT connection)

- Connection state with phone
- Button press events
- Catch / spin notifications
- Battery level
- Firmware version

## Identity Hashing

```
stableKey      = "pokemon_go_plus:<mac>"
identifierHash = SHA256(stableKey)[:16]
```

MAC rotation collapses identity across rotations: future work can correlate
the per-unit byte at payload offset 9 of the iOS-observed advertisement to
collapse identity across BD_ADDR rotations.

## Detection Significance

- Indicates a Pokemon GO player nearby with the original 2016 Pokemon GO
  Plus accessory
- Active BLE advertisement when powered on; advertises continuously when
  not paired and in pairing mode
- Battery-powered (CR2032), may not always be broadcasting

## References

- [Bluetooth SIG company identifiers](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — `0x0553` = Nintendo Co., Ltd.
- [Reverse Engineering Pokemon GO Plus — Tinyhack (2018)](https://tinyhack.com/2018/11/21/reverse-engineering-pokemon-go-plus/) — confirms DA14580 radio and the `Pokemon GO Plus` advertised name
- [Hacking the Pokemon GO Plus Over-the-Air — coderjesus](https://coderjesus.com/blog/pgp-suota/) — documents the `21c50462-67cb-63a3-5c4c-82b5b9939aef` SUOTA service from the Dialog Semi DA1458x SDK
- FCC ID **BKEPTC-001** (fccid.io/BKEPTC-001) — original Pokemon GO Plus
  test report
