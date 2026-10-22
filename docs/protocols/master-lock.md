# Master Lock Bluetooth Padlocks & Lock Boxes (Vault Home)

## Overview

Master Lock BLE padlocks and lock boxes pair with **Master Lock Vault Home**
(`com.masterlock.home.mlhome`, DexGuard-obfuscated SDK
`com.masterlock.mlbluetoothsdk`). They broadcast a **structured
manufacturer-data record** plus a 128-bit service UUID; the app parses it
before connecting. A passive observer reads SKU, a persistent 6-byte device
ID, firmware version and a key index, and can spot firmware-boot mode. Lock
state, battery and temperature are encrypted GATT only.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | read from the advert, **not hardcoded** in the app | The SIG registry (`src/adwatch/_bt_company_ids.py`) lists `0x014B` (331) = Master Lock; the report does not state the on-air value — **unverified**, confirm on a live capture. |
| Service UUID (128-bit) | two values, **runtime-decoded by DexGuard** | Not recoverable statically. One of them (compared against a decoded constant) flags firmware-boot mode. |
| Local name | not used | No name prefix/decoding |

### Manufacturer Data

Per the report, offsets are into `record.getData()` **including** the 2-byte
company ID. Minimum 16 bytes; a 17th byte adds the key index. All
little-endian.

| Offset | Field | Size | Decode |
|---|---|---|---|
| 0–1 | Company ID | 2 | uint16 LE |
| 2–5 | SKU | 4 | uint32 LE (product model) |
| 6–11 | Device ID | 6 | 6-byte LE — **persistent per-lock ID** |
| 12–15 | Firmware version | 4 | uint32 LE |
| 16 | Key index | 1 | uint8, optional (payload ≥ 17) |

In adwatch terms (`RawAdvertisement.manufacturer_payload` excludes the CID),
subtract 2: SKU @0, device ID @4, firmware @10, key index @14.

## What We Can Parse from Advertisements

SKU (model), 6-byte device ID, firmware version, key index, and
firmware-boot mode (alternate UUID128).

## What Requires GATT Connection

`StartSession` then encrypted `ReadPrimaryLockState`, `ReadBatteryLevel`,
`ReadTemperature`; unlock needs the cloud-provisioned session key and rolling
nonce (see `reports/masterlock-home-mlhome.md`).

## Identity Hashing

```
identifier = SHA256("masterlock:" + device_id_hex)[:16]
```

The 6-byte device ID is the stable per-lock key.

## Detection Significance

- Persistent device ID in cleartext → durable tracking of a lock and linking
  it to a place.
- SKU + firmware exposed → targeting of known-vulnerable firmware.
- Firmware-boot mode observable → reveals a mid-update window.
- Metadata only; does not by itself grant unlock.

## adwatch Status

No plugin. Future plugin: match the CID once confirmed live (expected
`0x014B`), require ≥ 14-byte payload after CID, decode SKU / device ID /
firmware / key index. Service UUIDs need Stage 6d recovery (Frida on
`Scanner.bluetoothReady()` / `GattCallback.a()`, live `getServiceUuids()`, or
`libbbafbc.so`).

## References

- apk-ble-hunting `reports/masterlock-home-mlhome_passive.md` (GATT/crypto: `reports/masterlock-home-mlhome.md`)
- App code cited: `com/masterlock/mlbluetoothsdk/bluetoothscanner/Scanner.java:190-197`; `.../internal/ClientDevice.java:63-65,71-80,84`
