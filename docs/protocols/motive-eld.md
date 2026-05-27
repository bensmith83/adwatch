# Motive (KeepTruckin) ELD BLE Protocol

## Overview

Motive Technologies, Inc. (formerly **KeepTruckin**) is a US commercial-fleet vendor that ships:

- Electronic Logging Devices (ELDs) for FMCSA hours-of-service compliance
- AI-powered dashcams (Smart Dashcam)
- Vehicle gateways (OBD-II + Bluetooth + LTE bridges)
- BLE asset tags for trailer and cargo tracking

Motive is registered with the Bluetooth SIG as the owner of UUID **`0xFC6D`**. Their devices appear in casual BLE scans because vehicle gateways and asset tags advertise continuously so the driver's Motive iOS/Android app can auto-pair.

## Identifiers

- **Service UUID:** `FC6D` (16-bit, SIG-allocated to "MOTIVE TECHNOLOGIES, INC.")
- **Local name pattern:** asset / VIN-style code, observed e.g. `AABL36UG028367` (4 alpha + 2 alnum + 6-8 digits)
- **Device class:** `vehicle_telematics`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `FC6D` (full: `0000fc6d-0000-1000-8000-00805f9b34fb`) | Motive SIG assignment |
| Manufacturer data | `0F 00` | 2-byte chipset signature (looks like Broadcom CID `0x000F` but is a SoC fingerprint, not a SIG-registered CID for Motive) |
| Local name | `<asset tag>` | Stable identifier for the physical hardware |

### Asset-tag structure

Captured: `AABL36UG028367`

Breakdown (heuristic, based on Motive support documentation):

| Substring | Meaning |
|-----------|---------|
| `AABL` | Fleet / customer prefix (often 4 alpha) |
| `36UG` | Hardware revision / SKU |
| `028367` | Serial number |

Other observed Motive asset codes follow the same general "4 alpha + 2 alnum + 6-8 digits" shape. The tag is the **stable identity** of the hardware — Motive recycles MAC addresses across replacements, but the asset code tracks the physical unit and survives swaps.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid `FC6D` | Motive device nearby |
| Asset tag | local_name | When advertised; the stable identity |
| Vendor | constant | `Motive` |

### What We Cannot Parse (requires GATT / Motive cloud)

- GPS position / heading / speed
- Engine telematics (RPM, fuel, fault codes)
- Driver identity / hours-of-service status
- Crash / hard-brake event flags
- Dashcam media references
- Account / fleet identifiers (beyond the asset-tag prefix)

## Sample Advertisements

```
Asset tag AABL36UG028367 — 6 sightings, one persistent unit
  Service UUID: FC6D
  Manufacturer data: 0f00
  Service data: (none)
```

## Identity Hashing

```
# When asset tag is advertised:
identifier = SHA256("motive:asset:{asset_tag}")[:16]

# When asset tag is unavailable:
identifier = SHA256("motive:mac:{mac}")[:16]
```

The asset-tag derivation keeps identity stable even if the BLE MAC rotates between sightings (Motive firmware uses random resolvable addresses on some product lines).

## Detection Significance

- Indicates a commercial-vehicle gateway, ELD, or trailer asset tag in the area
- A persistent FC6D + named asset tag is almost always a Motive-equipped truck or trailer parked nearby
- Adjacent vendors covered in this app: Procon Analytics, Autophix OBD2, Fixd OBD2, Xirgo ELD, FedEx SenseAware

## Parsing Strategy

1. Match on service UUID `FC6D` (short or 128-bit canonical form)
2. Extract `asset_tag` from `local_name` when present
3. Derive `identifier_hash` from the asset tag when available (so identity is stable across MAC rotations), else fall back to MAC
4. Return device class `vehicle_telematics` with `vendor=Motive`

## References

- [Motive](https://gomotive.com/) — manufacturer website
- [Bluetooth SIG 16-bit UUID list — member UUIDs](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — `0xFC6D → MOTIVE TECHNOLOGIES, INC.`
- Observed in `research/adwatch_export 12.json` — one persistent unit, 6 sightings over the capture window
