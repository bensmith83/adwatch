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
| Subtype byte | `0x08` | Constant across all sightings — Aruba subtype identifier. |
| Vendor magic | `1a f0 29 51 4b 83 01 00` | 8-byte constant; required for positive identification. |

The 8-byte vendor magic is not publicly documented but is identical across every Aruba sighting in our dataset; we treat it as part of the parser's match condition so we won't false-positive on other 0x011B traffic.

### Manufacturer Data Layout (19 bytes after company ID)

```
Offset 0     : 0x08            — subtype / version (constant)
Offset 1..4  : UU UU UU UU     — 4-byte stable unit ID (the tag's identity)
Offset 5..12 : 1a f0 29 51 4b 83 01 00 — 8-byte vendor magic (constant)
Offset 13    : 0x00            — reserved / pad
Offset 14..15: TT TT           — uptime counter (LE uint16, ~1 Hz)
Offset 16..17: 00 00           — reserved / pad
Offset 18    : 0xFF            — tail sentinel (possibly TX-power default −1 dBm)
```

### Unit ID

The 4-byte unit ID at offset 1..4 is **the** stable identifier — CoreBluetooth rotates the BLE MAC, but the unit ID persists across MAC rotations and tag reboots. It is the right field to key the device on.

Three of the four observed unit IDs end with the suffix `af7ba0`, strongly suggesting a vendor-allocated ID block — Aruba mints serials inside a small numeric range per production batch.

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
