# Trimble Surveying / GNSS Plugin

## Overview

[Trimble Inc.](https://www.trimble.com/) is a professional positioning and geospatial-tools vendor. Their BLE-capable product line spans:

- **Survey GNSS receivers** (R-series, Catalyst DA2 sub-meter receiver).
- **Construction lasers / total stations**.
- **Agriculture guidance modules** (GFX displays, NAV-900 receivers).
- **Mobile asset trackers**.

All of these advertise with a `local_name` of `"Trimble <6-10 digit serial>"`, which is the field-printed serial sticker on the case. This parser surfaces that serial as the device's stable identity.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `^Trimble \d{6,10}$` | E.g. `"Trimble 11006144"`, `"Trimble 23052162"`. |
| Company ID | `0x03FD` (when present) | Manufacturer data is optional — many sightings carry only the local name in a scan response. |

### Manufacturer Data

When present, the manufacturer payload begins with company ID `0x03FD` and includes a length-prefixed ASCII string that appears to be an internal model identifier. Example:

```
fd 03 | 01 05 | 34 38 35 33 30 42 | 0a
SIG    flags?   "485330B"            ?
```

We surface that ASCII run as `model_ascii` when present but treat its meaning as unconfirmed.

## Detection Significance

- **Construction sites, surveying crews, agriculture fields.** A Trimble advertisement in the wild is a strong signal of professional surveying or construction work nearby.
- **High-value equipment.** Trimble GNSS receivers run thousands of dollars; the serial number lets a field crew positively identify their own gear vs. another contractor's.
- **Stable serial enables tracking.** The serial in the local name is the unit's permanent ID and rolls neither with the MAC nor across reboots.

## What We Cannot Parse from Advertisements

- Position data — GNSS positions are exchanged over the GATT connection to the Trimble Mobile or Trimble Connect apps, not in the advertisement.
- Receiver model — Trimble doesn't include the marketing model name in the advertisement; you can correlate the serial to a model via Trimble's My Account portal but not from the BLE traffic alone.

## References

- [Trimble GNSS receivers](https://geospatial.trimble.com/en/products/hardware)
- [Trimble Mobile Manager (companion app)](https://apps.apple.com/us/app/trimble-mobile-manager/id1124884787)
