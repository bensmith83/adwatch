# Bee AI Pendant (Bee / Bee Frontier)

## Overview

**Bee** (`com.bee.android`; Bluush Inc., Amazon-owned) is an always-listening
AI wearable pendant. The app shell is React Native, but BLE lives in a bespoke
Kotlin module (`com.bee.background.*`) on raw `android.bluetooth.*`, so the
evidence is cited Java (HIGH confidence).

The passive surface is a **single advertised 16-bit service UUID, `0xD5C4`**.
No manufacturer data, no service data, no name prefix. Everything else
(battery, state, firmware, AES-128-CTR audio) is connection-only.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID (16-bit) | `0xD5C4` (`0000d5c4-0000-1000-8000-00805f9b34fb`) | Short-form alias of the full custom service `03D5D5C4-A86C-11EE-9D89-8F2089A49E7E`. Non-SIG custom value; not in adwatch's UUID table. Scan filter at `module/BeeScanController.java:209`, def `BeeBackgroundModule.java:561`; also the CompanionDeviceManager filter (`BeeBackgroundModule.java:1590-1594`). |
| Company ID | — | Zero `getManufacturerSpecificData`/`getServiceData`/`ScanRecord` hits in the BLE module |
| Local name | — | Not used for discovery |

Reconnect after bonding is **MAC-pinned** (`ServiceReconnectController.java:399`).

## What We Can Parse from Advertisements

Presence only ("a Bee pendant is nearby").

## What Requires GATT

Control characteristic `05e1f93c-…` (write + notify): battery/charge
(`0xC00F`, event `0x8001`), device state recording/mute/sleep (`0xC006`, event
`0x8002`), charging (`0x8000`), button events (`0x8003`/`0x8004`), firmware
(`0xC005`). Audio is a notify on `b189a505-…`, AES-128-CTR with a cloud-minted
key.

## Identity Hashing

No in-advert identifier. `SHA256("bee:{mac}")[:16]` — the app treats the
address as stable (MAC-pinned reconnect).

## Detection Significance

- A one-bit "this person is wearing an always-on microphone" signal, broadcast
  continuously with no rotating identifier.
- 16-bit UUIDs are collision-prone; if false positives appear, corroborate
  post-connect via the full 128-bit service and the `05e1f93c` / `b189a505`
  characteristics (out of scope for a passive scanner).

## adwatch Status

No plugin. A future plugin would match service UUID `d5c4` and report presence
only.

## References

- apk-ble-hunting `reports/bee-android_passive.md` (and `reports/bee-android.md`)
- Code cited by the report: `com/bee/background/BeeBackgroundModule.java`
  (`:561`, `:1590-1594`, `:1738`), `module/BeeScanController.java:209`,
  `ServiceReconnectController.java:399`
