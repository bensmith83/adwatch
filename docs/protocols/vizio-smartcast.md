# Vizio SmartCast Mobile App (TV Companion Beacon)

## Overview

VIZIO Inc. ships **SmartCast** — the firmware on its modern smart TVs
plus an iOS/Android companion app called "VIZIO Mobile App". The app
acts as a remote control, casting / DIAL launcher, settings panel, and
quick-pair device for SmartCast TVs and Vizio SmartCast soundbars.

While the app is in the foreground (or recently backgrounded), it
advertises a BLE peripheral so a nearby Vizio TV can complete a
**proximity-pair handshake** without requiring the user to type a PIN.
The actual control plane — TV state, app launches, input switching —
runs over Wi-Fi (HTTPS on port 7345/9000); BLE is presence + pairing
only.

The advertised peripheral is the **phone**, not the TV. The TV
discovers the phone, not the other way around. That makes the
fingerprint useful for "who's in the room with what device" mapping but
not for inventorying SmartCast TVs (which advertise different shapes
under Wi-Fi).

## Captured Surfaces

Three surfaces observed in `research/nearsight_export 2.json` (8
sightings across 2 distinct phones):

| Surface | localName | serviceUUIDs | manufacturerData | Cause |
|---------|-----------|--------------|------------------|-------|
| A | `VIZIO Mobile App` | `EA1979CF-5313-4152-B056-37619C1DA100` | `5800` | App in foreground, full advertisement |
| B | `VIZIO Mobile App` | (empty) | (absent) | iOS backgrounded the app — CoreBluetooth stripped the UUID and mfg fields, kept the name |
| C | (none) | `EA1979CF-…` | (absent) | iOS backgrounded the app — CoreBluetooth stripped the name, kept the UUID |

The multi-surface pattern is the canonical iOS `CoreBluetooth`
peripheral lifecycle: when the source app loses foreground, the OS
shuffles which advertisement fields it emits, so a single SmartCast
install appears to a passive scanner as multiple "devices".

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `VIZIO Mobile App` | Exact match; set by the iOS/Android app |
| Service UUID | `EA1979CF-5313-4152-B056-37619C1DA100` | Vizio vendor-defined; not in BT SIG `member_uuids.yaml`. UUIDv4 (random) |
| Manufacturer data | `58 00` (sometimes) | SIG CID `0x0058` = Bluegiga Technologies OY (now Silicon Labs). This is an **SDK default**, not evidence of Vizio silicon — it propagated through some component Vizio integrated. We surface it as a forensic hint, not an attribution |
| Address type | `random` | iOS resolvable private address |

The parser matches when **either** the vendor UUID is present **or**
the localName is exactly `VIZIO Mobile App`. CID 0x0058 alone is too
noisy (generic Bluegiga / Silicon Labs dev modules) and is never used
as a sole gate.

### What We Can Parse

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Vizio` |
| Product family | hard-coded | `SmartCast Mobile App` |
| Device class | hard-coded | `tv_companion_app` |
| Telemetry | hard-coded | `presence_only` |
| `match_mode` | which gate fired | `uuid_and_local_name` / `vendor_uuid` / `local_name` |
| `vendor_service_uuid` | hard-coded (emitted when UUID-matched) | for downstream attribution |
| `local_name` | localName | when present |
| `company_id` / `company_id_note` | CID byte | only when 0x0058 is observed |

### What We Cannot Parse from the Advertisement

- The model of the Vizio TV in range (TVs don't broadcast over BLE).
- The phone model / OS / app version.
- Cast / mirroring state.
- Account identity or any SmartCast user metadata.

All of that lives behind the Wi-Fi control plane. The advertisement
proves only that a phone running the VIZIO Mobile App is nearby.

## Stable Identity

When the vendor UUID is present (surfaces A and C), we anchor stable
identity on the UUID:

```
stable_key = vizio_smartcast:uuid
```

This intentionally **collapses all VIZIO Mobile App phones in range
into a single stable key**. The vendor UUID is per-app, not per-phone
— there is no per-device entropy in the advertisement to disambiguate
two phones running the same install of the app. Distinct phones will
share the same `stable_key` and only be distinguished by their
(rotating) MAC for the duration of one privacy window.

When only the name matches (surface B — UUID was scrubbed), we fall
back to:

```
stable_key = vizio_smartcast:mac:<mac>
```

The name-only surface will appear as a separate row until the same
phone re-enters the foreground and re-broadcasts the UUID.

## Detection Significance

- Presence of a `vizio_smartcast` device in a forensic timeline
  indicates a person carrying an iOS/Android phone with the VIZIO
  Mobile App installed and recently used to control a SmartCast TV or
  soundbar.
- The app remains in CoreBluetooth's adv schedule for a short window
  after backgrounding, so sightings often persist a few minutes after
  the user puts their phone down.
- Multiple `vizio_smartcast` MACs in one room is a strong signal of a
  multi-person household where ≥2 people have paired the app to the
  same TV.

## References

- [VIZIO Mobile App product page](https://www.vizio.com/en/mobile)
- [pyvizio (third-party SmartCast Wi-Fi API)](https://github.com/raman325/pyvizio) — documents the HTTPS control plane that complements this BLE pair handshake
- [exiva/Vizio_SmartCast_API](https://github.com/exiva/Vizio_SmartCast_API) — earlier RE of the SmartCast pairing flow
- [BT SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/HEAD/assigned_numbers/company_identifiers/company_identifiers.yaml) — confirms `0x0058 = Bluegiga Technologies OY` (now Silicon Labs)
- [Apple `CBAdvertisementDataOverflowServiceUUIDsKey` docs](https://developer.apple.com/documentation/corebluetooth/cbadvertisementdataoverflowserviceuuidskey) — background on iOS CoreBluetooth field shuffling
- Nearsight export: `research/nearsight_export 2.json`, 8 sightings, 2 phones (2026-06-04 to 2026-06-05)
