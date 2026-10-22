# Kiiroo / Feel Connected Devices (FeelConnect 3.0)

## Overview

Kiiroo intimate devices (Keon, Titan, Onyx, Pearl, Edge, Esca/Esca2, Fuse)
pair with **FeelConnect 3.0** (`com.feeltechnology.feelconnect3`, React
Native / Hermes). Devices are **connectable and advertise continuously while
powered on**, identifiable by a model-name local name and/or a Kiiroo 128-bit
service UUID. Long-distance/interactive sync goes through an AWS cloud bridge,
not over the air.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID (128-bit) | `88f80580-0000-01e6-aace-0002a5d5c51b` | Kiiroo service family, "if advertised" (report) |
| Service UUID (128-bit) | `88f82580-0000-01e6-aace-0002a5d5c51b` | Newer family |
| Legacy service UUIDs | TI `F000BB03-…` / `F000C000-…` on base `…-0451-4000-b000-000000000000` | Older units; TI base is generic, not Kiiroo-specific |
| Local name | `Keon`, `Titan`, `Onyx`, `Pearl`, `Edge`, `Esca`/`Esca2`, `Fuse` | No uniform vendor prefix ("FC" is the app, not the device) |
| Company ID | *(unknown)* | SIG registry (`src/adwatch/_bt_company_ids.py`) lists `0x05A5` = Kiiroo BV, but the report recovered **no** manufacturer-data parsing — MSD unknown pending live capture |

The `…-aace-0002a5d5c51b` suffix is shared with some other (CSR/Cambridge
heritage) devices — disambiguate by the `88f8…` prefix. Bare model names
such as `Edge`, `Pearl`, `Fuse` are generic words and collide easily; require
the service UUID or treat name-only matches as low confidence.

## What We Can Parse from Advertisements

| Field | Source |
|-------|--------|
| Kiiroo device present | `88f8…` service UUID |
| Exact model | local name |

No live motor/position state is broadcast.

## What Requires GATT Connection

Motor control and position/sensor data (GATT notify after connect).

## Identity Hashing

```
identifier = SHA256("kiiroo:" + mac)[:16]
```

## Detection Significance

**High.** A continuously broadcast model name or Kiiroo UUID lets a passive
scanner detect and identify a specific intimate device in range — presence
tracking / outing risk, especially with a static MAC.

## adwatch Status

No plugin. Future plugin: match the two `88f8…580-0000-01e6-aace-0002a5d5c51b`
UUIDs (primary), model-name set as enrichment; capture raw MSD to check for
CID `0x05A5`.

## References

- apk-ble-hunting `reports/feeltechnology-feelconnect3_passive.md`
- adwatch: `src/adwatch/_bt_company_ids.py` (`0x05A5: 'Kiiroo BV'`)
