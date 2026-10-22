# igloohome Smart Locks

## Overview

igloohome smart deadbolts, padlocks and lock boxes pair with the igloohome
app (`com.igloo.home`). The **primary** BLE stack is igloohome's first-party
SDK `co.igloohome.ble.lock`, which scans for and parses its own **9-byte
manufacturer-data** record under company ID `0x05BA`. A bundled
TTLock/Sciener SDK (`co.igloohome.legacy.ble.*`) covers legacy units.

> **Record correction (report's Stage 5b audit, batch 29):** an earlier
> draft of the report described the TTLock advert and claimed `isUnlock` +
> battery are advertised. Both are wrong — those come from post-connect,
> decrypted GATT buffers on the legacy stack. Do not attribute an
> open/closed-door passive leak to igloohome.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x05BA` (1466) — igloohome | Matches `src/adwatch/_bt_company_ids.py`. Wire bytes `BA 05`. |
| Service UUID (128-bit) | `5c3a1523-897e-45e1-b016-007107c96df6` | Also the GATT service |
| Local name | not used for first-party discovery | Read for display only |
| Legacy (TTLock) name | `LOCK_` prefix (case-insensitive) + service `0x1910` | BONG wristband variant: `6e400001-…-e50e24dcca1e` (Nordic UART base) |

App ScanFilter: service `5c3a1523` **and** manufacturer `0x05BA` with
data `00 01 00 02 00 00 00 00 00` / mask `01 00 00 00 00 00 00 00 00` — the
mask only constrains the low bit of byte 0, so effectively "CID `0x05BA`
present AND service `5c3a1523` present".

### Manufacturer Data (after CID, exactly 9 bytes)

The parser throws `"expected 9"` on any other length.

| Offset | Field | Size | Decode |
|---|---|---|---|
| 0 | reserved | 1 | always `0x00` |
| 1 | protocolMajorVersion | 1 | uint8 |
| 2 | protocolMinorVersion | 1 | uint8 (gates optional flags) |
| 3 | lockType | 1 | uint8; when proto ≥ v1.5, high bit `0x80` masked off and reused as `isModule` |
| 4 | customerProperties | 1 | per-customer byte |
| 5 | lockVersion | 1 | firmware/version id |
| 6 | dfuRevisionNumber | 1 | DFU/bootloader revision |
| 7 | vendorId | 1 | vendor id |
| 8 | **status flags** | 1 | bitfield below |

#### Status byte (offset 8)

| Mask | Flag | Meaning | Availability |
|---|---|---|---|
| `0x01` | `pairedStatus` | claimed/paired (clear = **unclaimed & claimable**) | always |
| `0x10` | `active` | lock active/awake | always |
| `0x40` | `hasActivityLogs` | unread activity logs waiting | proto v1 minor ≥ 2, or v2 |
| `0x80` | `isModule` | module variant | proto v1 minor ≥ 5 (per report: `utils/n.java:34-38`) |

The report places `isModule` both in byte 3's high bit and in the status
table; treat its exact location as needing live-capture confirmation.

## What We Can Parse from Advertisements

Protocol version, lock type, vendor/customer/version/DFU bytes, and
`pairedStatus` / `active` / `hasActivityLogs` / `isModule`.

**Not in the advert:** open/closed (`isUnlock`) and battery — post-connect
GATT only.

## What Requires GATT Connection

Lock/unlock, battery, access roles, logs; offline-PIN ("algoPIN") logic may
live in Dart `libapp.so`. See `reports/igloo-home.md`.

## Identity Hashing

No per-unit serial in the record; combine MAC with the fixed fingerprint:

```
identifier = SHA256(f"igloohome:{mac}:{lockType}:{vendorId}:{customerProperties}")[:16]
```

## Detection Significance

- **Claimable-lock signal:** `pairedStatus == 0` advertises an unclaimed
  lock — the window in which an attacker could try to claim it first.
- Fixed model/vendor bytes + MAC → persistent identification of a lock at a
  location (subject to device-side MAC randomisation).
- `active` / `hasActivityLogs` reveal coarse usage.

## adwatch Status

No plugin (CID `0x05BA` only appears in the company-ID table). Future
plugin: match CID `0x05BA` (+ service `5c3a1523-…`), require 9-byte payload,
decode the table above; optionally a legacy TTLock matcher on `LOCK_` +
`0x1910`.

## References

- apk-ble-hunting `reports/igloo-home_passive.md` (full UUID catalog in `reports/igloo-home.md`)
- App code cited: `co/igloohome/ble/lock/scanner/lock/c.java:156,198,204-209`; `co/igloohome/ble/lock/utils/a.java:21-27,66`; `utils/n.java:24-43`; `utils/m.java:22-38,94`; legacy `com/ttlock/bl/sdk/scanner/a.java:61`, `com/ttlock/bl/sdk/service/BluetoothLeService.java:1188,1913,2017,2027,2120,2134`
