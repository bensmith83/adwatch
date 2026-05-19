# Bose FEBE Earbud / SoundLink Plugin

## Overview

Bose's newer product lines — **QC Ultra Earbuds**, **Open Earbuds Ultra**, and likely the SoundLink Micro 2 / Frames generation — advertise under a different Bluetooth SIG company identifier (`0x009E`) than the older Bose audio devices the existing `BoseParser` covers (`0x0065`). They consistently co-advertise SIG member service UUID `0xFEBE` (Bose Corporation's secondary service).

This parser is a sibling of `BoseParser`: both vend "is this a Bose audio device?" classifications, but they decode different on-wire formats from different SIG IDs. We chose a separate parser rather than extending `BoseParser` because the payload structure is sufficiently different that a unified parser would be twice as complex with no benefit.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x009E` | Newer Bose SIG identifier. |
| Service UUID | `0xFEBE` | SIG-registered to Bose Corporation. |
| Local name (when broadcast) | `"Bose Open Earbuds Ultra"`, `"Bose QC Ultra Earbuds"`, … | User-renameable in the Bose Music app. |

### Manufacturer Data Layout (9 bytes after company ID)

```
Byte 0     : flags / record-version (0x00 in all observed captures)
Byte 1     : product code (varies per SKU)
Byte 2     : 0x06 (model-family magic byte; constant)
Bytes 3..8 : 6-byte per-device rolling hash
```

### Product Code Map

| `product_code` | Observed local name |
|---|---|
| `0x24` | `"Bose QC Ultra Earbuds"` (and a user-renamed instance: `"Niggapods"`) |
| `0x82` | `"Bose Open Earbuds Ultra"` |
| `0x2C` | (no local name captured) |

The parser surfaces `suggested_product` for known codes and `renamed = true` when the device's local name doesn't start with one of the official Bose prefixes (`"Bose "`, `"LE-Bose "`, `"LE-"`).

### Rolling Hash

The trailing 6 bytes change between consecutive sightings of the same physical earbud — so they are **not** a stable device serial. They look like a 48-bit rolling identifier the Bose Music app validates during pairing. Within a short time window, two consecutive ads from the same earbud share the same hash; that's enough to use as a same-burst stable key but you should not expect it to persist across reboots.

## Detection Significance

- **High-end personal audio in earshot.** Bose QC Ultra and Open Earbuds Ultra retail at $300+; their presence in a scan is a strong consumer-electronics signal.
- **Renamed earbuds are common.** The "Niggapods" sample in our dataset is an extreme example, but renaming earbuds via the Bose Music app is a routine personalization — we flag renamed devices with `renamed = true` so downstream tooling can decide whether to display the user-supplied name.

## What We Cannot Parse from Advertisements

- Per-unit serial — the 6-byte hash is rolling, not a stable serial. To get a true serial number you'd need to GATT-connect and read the Device Information service.
- Battery / charge state — likely in the GATT vendor service, not in the advertisement.

## Coexistence with BoseParser

This parser handles SIG CID `0x009E` and the `0xFEBE` service UUID. The existing `BoseParser` handles SIG CID `0x0065` (older Bose product lines: SoundLink, QC 35/45, Frames) and the `0xFE78` service UUID. They cover disjoint Bose product generations and do not conflict.

## References

- [Bluetooth SIG member UUIDs (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — confirms `0xFEBE = Bose Corporation`.
- [Bose QC Ultra Earbuds product page](https://www.bose.com/p/quietcomfort-ultra-earbuds)
- [Bose Music app](https://www.bose.com/c/bose-music-app)
