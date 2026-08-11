# Escort (Cedar Electronics) radar / laser detector

## Overview

**Escort** makes consumer radar/laser detectors (MAX series, Redline, iX,
etc.) that pair with the **Escort Live / Drive Smarter** mobile app over BLE
to share crowd-sourced speed-trap and red-light-camera alerts. Escort and
**Cobra** are both **Cedar Electronics** brands and share the Drive Smarter
app stack — so this is the Escort sibling of the existing
[Cobra parser](cobra.md) (different UUIDs).

Escort has no Bluetooth SIG company ID and emits no manufacturer data; the
BLE fingerprint is a single proprietary 128-bit service UUID plus the
marketing model name in the GAP local-name slot.

## Supported / observed models

| Model | Local name | Device class |
|---|---|---|
| Escort MAX 3 | `MAX 3` | radar/laser detector |
| other MAX-series | `MAX …` | radar/laser detector |
| other Escort | (model name) | radar/laser detector |

Only `MAX 3` has been observed directly; the UUID gate identifies any Escort
detector, with the model taken from the local name when present.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Service UUID | `B5E22DE9-31EE-42AB-BE6A-9BE0837AA344` | Proprietary 128-bit; the decisive anchor |
| Local name | marketing model name | e.g. `MAX 3` |
| Manufacturer data | none | no SIG CID assigned |
| Address type | `random` | rotating; model name is the stable identity |

**The service UUID alone is sufficient** (`MAX 3` etc. is too generic to
match on its own). Companion GATT characteristics `B5E22DEA` (tx) /
`B5E22DEB` (rx) carry the live alert/GPS stream but are never advertised.

### Why this UUID = Escort (attribution)

The service UUID appears **verbatim** as the constant
`escortBLEServiceUUID = "B5E22DE9-31EE-42AB-BE6A-9BE0837AA344"` in the
open-source **`koiosdigital/RoadSage`** project (with the DEA/DEB
characteristics), and the same UUID family appears in **`grabercn/Car-HUD`**
(`b5e22deb-…` alert characteristic). The observed local name `MAX 3` matches
the retail **Escort MAX 3** detector. Escort + Cobra are both Cedar
Electronics brands, consistent with the shared Drive Smarter app stack.

### What we can surface

| Field | Source | Notes |
|---|---|---|
| `vendor` | hard-coded | `Escort (Cedar Electronics)` |
| `model` | localName | e.g. `MAX 3` |
| `product_family` | localName | `Escort MAX radar/laser detector` for MAX-series |
| `service_uuid` | hard-coded | the proprietary anchor |

### What we cannot surface

- Live radar/laser alerts, threat band, GPS, settings — streamed only over
  the DEA/DEB GATT characteristics on an app connection we never make.

## Parser scope (passive only)

Presence + model identification only. Mirrors `CobraParser`
(`rawPayloadHex = ""`, no decode).

## Stable identity

```
stable_key = escort:<model name>    (name present)
stable_key = escort:mac:<mac>       (name absent)
identifier = SHA256(stable_key)[:16]
```

## Detection significance

- A radar detector is a strong **in-vehicle** context clue (the detector
  advertises while waiting for the Drive Smarter app to connect).
- Distinct from the sibling Cobra detectors/dash cams by UUID, so attribution
  stays brand-accurate within Cedar Electronics.

## References

- [`koiosdigital/RoadSage` — `escortBLEServiceUUID` constant](https://github.com/koiosdigital/RoadSage) (EscortConstants / BluetoothManager: service `B5E22DE9-…`, chars `B5E22DEA`/`B5E22DEB`)
- [`grabercn/Car-HUD`](https://github.com/grabercn/Car-HUD) — same UUID family (`b5e22deb-…` alert characteristic)
- [Escort MAX 3 (Crutchfield)](https://www.crutchfield.com/p_036MAX3/Escort-MAX-3.html)
- [Cedar Electronics — Escort brand](https://cedarelectronics.com/brands/escort/)
- Captures: `research/nearsight_export 7.json` (1 unit, 107 sightings).
