# Owlet Baby Care (Infant Monitor / Cam / Base Station)

## Overview

Owlet Baby Care Inc. is a Utah-based juvenile-product company best known
for the **Smart Sock** (infant pulse-oximeter sock that streams SpO2,
heart rate, and sleep state to a phone), the follow-on **Dream Sock**,
the **Owlet Cam** wifi/BLE nursery camera, and the **Owlet Base
Station** that pairs with the sock. All four ship with Bluetooth Low
Energy for setup, sock-to-base pairing, and short-range telemetry.

The advertisement carries Owlet's BT-SIG-assigned company identifier
plus a vendor-specific 128-bit service UUID. Real-time infant
vitals are not exposed in the advertisement; they live behind the
vendor GATT service (paired) and the proprietary cloud API.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `OB` | "Owlet Baby" abbreviation; 2 chars, too generic to use alone |
| Manufacturer CID | `0x0E9F` | Little-endian `9F 0E` — BT SIG `company_identifiers.yaml`: "Owlet Baby Care Inc." |
| Manufacturer payload | 2-30 bytes of zeros (observed) | Idle / pre-pairing state — sock-active state would carry SpO2 / HR bytes here |
| Service UUID | `C5163C4B-9B63-570D-A3A8-407716F04276` | Owlet vendor-defined GATT service (not in BT SIG `member_uuids.yaml`) |
| Service data | (absent in observed captures) | — |
| Address type | `random` | rotating private address |

Observed payload forms (`research/nearsight_export.json`, 1 unit, 3 sightings):

- `9f0e0000000000000000000000000000000000000000000000000000000000` (32 bytes — full idle)
- `9f0e0000` (4 bytes — minimum-length advertisement)

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Owlet Baby Care` |
| Product family | hard-coded | `Smart Sock / Dream Sock / Cam / Base` (advertisement doesn't disambiguate) |
| Device class | hard-coded | `infant_monitor` |
| Vendor service UUID | hard-coded | `C5163C4B-9B63-570D-A3A8-407716F04276` |
| Device state | manufacturer payload | `idle` if all post-CID bytes are zero, `active` otherwise |
| Raw payload | manufacturer payload | Hex of bytes after the 2-byte CID (for forensic snapshotting) |

### What We Cannot Parse from the Advertisement

- Live SpO2, heart rate, skin temperature, motion, or sleep state.
- Sock-on-foot / battery / charging status.
- Per-unit serial number (the advertisement carries no per-device
  identifier — only the rotating MAC).
- Specific product (Sock vs Cam vs Base) — the CID + UUID + name are
  shared across the product line.

All real vitals live under the `C5163C4B-…` GATT service plus the
Owlet cloud API; both are proprietary. The parser deliberately stops
at presence + coarse activity state.

## Stable Identity

No per-unit serial is broadcast. The parser keys off the rotating
random MAC, which means cross-session continuity is best-effort:

```
stable_key = owlet_baby_care:mac:<mac>
```

For longer-lived identity, downstream code can rely on the consistent
presence of the vendor UUID + CID pair to bucket sightings into "an
Owlet device at this location," even when the MAC churns.

## Detection Significance

- **Strong infant-in-residence signal.** Owlet's entire product line
  targets sleeping babies (the sock is sized for 0-18 months; the cam
  is a nursery cam). A confirmed Owlet sighting is one of the most
  reliable indirect demographic indicators in BLE space — far stronger
  than e.g. a baby-monitor wifi SSID.
- **Useful for short-term-rental / shared-dwelling reconnaissance.**
  Detecting an Owlet device in an Airbnb, hotel room, or co-living
  space implies a child is present or recently present; relevant for
  privacy-and-children policy enforcement and for parents auditing
  who else is in their home network.
- **Possible health-data adjacency.** Owlet devices have a documented
  history of FDA scrutiny (Smart Sock recall + reclassification as a
  medical device in 2021); presence on a network implies vitals are
  being collected and uploaded to Owlet cloud.
- Random-address with vendor CID + 128-bit UUID and a 2-char generic
  local name is a recurring "consumer IoT bridge / hub" shape.

## References

- Owlet product line — <https://owletcare.com/products>
- Unofficial Owlet cloud-API reverse-engineering — <https://github.com/BastianPoe/owlet_api>
- BT SIG `company_identifiers.yaml` — `0x0E9F` = Owlet Baby Care Inc.
- BT SIG `member_uuids.yaml` (no entry for `C5163C4B-…` — vendor-defined,
  not registered)
- Capture: `research/nearsight_export.json`, 1 unit, 3 sightings
