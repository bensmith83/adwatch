# Aruba (HPE) Asset Track Beacon Plugin

## Overview

Bluetooth SIG company ID `0x011B` is registered to **Aruba Networks** (now HPE Aruba Networking). The captures here are consistent with an **enterprise indoor-location / asset-tracking deployment** — most likely the [HPE Aruba Networking AT-BT10-50](https://buy.hpe.com/us/en/Networking/Wireless-Devices/WLAN-Security/HPE-Aruba-Networking-Location-Beacon-Product/HPE-Aruba-Networking-AT%E2%80%91BT10%E2%80%9150-50%E2%80%91pack-of-Battery-Powered-Asset-Tracking-Bluetooth-Beacons/p/JX987A) "Asset Track" beacon (SKU `JX987A`, sold in 50-packs) or the BLE radios in Aruba 3xx/5xx-series access points forwarding telemetry to [Aruba Meridian / Aruba Location Services](https://www.arubanetworks.com/assets/ds/DS_LocationServices.pdf).

Twenty-seven distinct beacons in a single 48 h capture window is high enough density to confirm a dedicated indoor-location deployment, not an incidental device.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x011B` | Aruba Networks (SIG). |
| Payload length | 19 bytes (after the 2-byte company ID) | Fixed for the observed subtype. |
| Subtype byte | `0x08` | Constant across all `08`-frame sightings — Aruba subtype identifier. A second subtype `0x0a` (17-byte payload) exists and is not decoded. |
| Constant bytes | `51 4b 83 01 00` at offset 8..12 | Required for positive identification. |
| Embedded BD_ADDR OUI | `F0:1A:A0` (Hewlett Packard Enterprise) | Second attribution signal; recorded, not required. |

> **Correction (2026-08-23 sweep).** The first write-up described a 4-byte
> unit ID followed by an 8-byte vendor magic `1a f0 29 51 4b 83 01 00`. A
> third capture carried `1a f0 2f …` at those offsets and was rejected
> wholesale. Laid side by side, the three captures are
>
> | capture | bytes 1..6 (wire, LE) | → BD_ADDR | byte 7 |
> |---|---|---|---|
> | 2026-07 A | `xx xx xx a0 1a f0` | F0:1A:A0:xx:xx:xx | `0x29` |
> | 2026-07 B | `xx xx xx a0 1a f0` | F0:1A:A0:xx:xx:xx | `0x29` |
> | 2026-08 (26 rec) | `xx xx xx a0 1a f0` | F0:1A:A0:xx:xx:xx | `0x2f` |
>
> `F0:1A:A0` is IEEE-registered to Hewlett Packard Enterprise. The "magic"
> straddled the address's last byte (`a0 1a f0` is the OUI in wire order),
> and byte 7 is a separate per-device field. The earlier observation that
> "three of four unit IDs end in `xxxxa0`" was this same OUI showing
> through. Only `51 4b 83 01 00` is actually constant.

### Manufacturer Data Layout (19 bytes after company ID)

```
Offset 0     : 0x08            — subtype / version (constant for this frame)
Offset 1..6  : M6 M5 M4 M3 M2 M1 — BD_ADDR, little-endian (OUI F0:1A:A0 = HPE)
Offset 7     : XX              — per-device field, meaning unknown (0x29, 0x2f seen)
Offset 8..12 : 51 4b 83 01 00  — 5-byte constant (the parser's match condition)
Offset 13    : 0x00            — reserved / pad
Offset 14..15: TT TT           — uptime counter (LE uint16, ~1 Hz)
Offset 16..17: 00 00           — reserved / pad
Offset 18    : 0xFF            — tail sentinel (possibly TX-power default −1 dBm)
```

### Unit ID / BD_ADDR

The embedded address is **the** stable identifier — CoreBluetooth rotates
the advertising MAC, but the burned-in address persists across rotations
and reboots. The parser surfaces the full address as `bd_addr` and keeps
its original `unit_id` (= the address's low four bytes in wire order, e.g.
`xxxxxxa0` for F0:1A:A0:xx:xx:xx) as the stable-key pre-image so the
layout correction needed no identity migration.

### Second frame shape (subtype `0x0a`, not decoded)

Three sightings on 2026-08-20 of a 17-byte 0x011B payload:

```
0a ec 1b 5f c9 XX XX a3 00 82 06 02 07 0a 01 77 cb
```

with bytes 5..6 varying (`ea dd`, `eb 04`, `dd c6`). Too few to separate a
counter from an identifier; the parser explicitly rejects it rather than
mis-decode it.

### Uptime Counter

The little-endian uint16 at offset 14..15 increments approximately once per second and rolls over every ~65,536 s ≈ 18 hours. We verified this empirically by tracking two distinct units across ~20 minutes of consecutive sightings: deltas matched 1 Hz to within scanning jitter.

We surface this as `uptime_seconds` so liveness (and a coarse "was the beacon power-cycled recently?" signal) is available. It is also useful as a per-device fingerprint within an 18 h window — the counter's phase is effectively a free identifier modulo wraparound.

## Detection Significance

- **Enterprise indoor-location signature.** A dense cluster of `0x011B` advertisements pinpoints buildings using Aruba Meridian / Aruba Location Services for asset tracking. Common sectors: hospitals (tracking IV pumps, infusion stands), warehouses (tracking pallets, forklifts), corporate campuses (tracking AV gear), retail (tracking inventory).
- **Stable plaintext unit ID enables tracking.** Despite `addressType = random`, the 4-byte unit ID is rotation-stable — anyone with a BLE scanner can re-identify each asset indefinitely. This is normal for asset-tracking beacons (the deployment owner *wants* this), but worth flagging when these devices appear outside the deployment owner's premises.

## What We Cannot Parse from Advertisements

- The actual asset metadata (which physical object the tag is attached to) — that's stored in the Aruba Meridian cloud and indexed by unit ID. The BLE traffic alone tells you "an asset is here", not "an MRI machine is here".
- TX power calibration, battery level — likely behind a GATT characteristic and not in the advertisement.

## References

- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — confirms `0x011B = Aruba Networks`.
- [HPE Aruba Networking Location Services data sheet](https://www.arubanetworks.com/assets/ds/DS_LocationServices.pdf)
- [HPE store — AT-BT10-50 Asset Track beacon (JX987A)](https://buy.hpe.com/us/en/Networking/Wireless-Devices/WLAN-Security/HPE-Aruba-Networking-Location-Beacon-Product/HPE-Aruba-Networking-AT%E2%80%91BT10%E2%80%9150-50%E2%80%91pack-of-Battery-Powered-Asset-Tracking-Bluetooth-Beacons/p/JX987A)
- [Aruba Meridian Beacons & Asset Tracking config guide](https://docs.meridianapps.com/hc/en-us/articles/360042543934-AOS-8-6-x-Meridian-Beacons-Management-and-Asset-Tracking-Configuration-Guide)
