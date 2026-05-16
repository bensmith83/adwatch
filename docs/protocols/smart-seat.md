# Smart Seat ("SSSeat" BLE Tag)

## Overview

A class of low-power BLE peripherals that broadcast under the local
name **`SSSeat`** with company ID `0x04C5` and a 10-byte
manufacturer-data payload. The captures match the shape of an
**ergonomic / posture-monitoring smart-seat product** — devices in
this category include smart office chairs, posture-correcting seat
covers (SitRight, SmartSeat.eu), and clinical posture-monitoring pads.

The specific vendor behind the `SSSeat` local name has not been
positively identified — the BT-SIG CID `0x04C5` and the `SSSeat`
naming convention are not publicly documented to a specific product.
The parser identifies the device class (`seat / posture monitor`)
and records the per-unit device identifier embedded in the payload,
but does **not** claim a vendor name.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x04C5` | Vendor not publicly identified |
| Local name | `SSSeat` | Stable across captures |
| Mfr-data length | 12 bytes (CID + 10 payload) | Stable shape |

## Wire Format (real-world captures)

Two captures of the same physical seat, observed within minutes of
each other at RSSI -91 / -92 (i.e. nearby, same device):

```
c5 04 04 85 80 01 ff 8b 92 14 70 ef       (38 sightings)
c5 04 04 84 80 01 ff 8b 92 14 70 ef       (7 sightings)
└─┬─┘ └─┬─┘ └┬┘ └────────┬────────┘
 cid   hdr  state    device-id (5 bytes)
```

| Offset (post-cid) | Bytes        | Meaning |
|-------------------|--------------|---------|
| 0                 | `04`         | Header / frame-type (constant in observed samples) |
| 1                 | `85` / `84`  | State byte — varies between captures (posture state? sensor toggle? counter) |
| 2–4               | `80 01 ff`   | Flags / config (constant) |
| 5–9               | `8b 92 14 70 ef` | Per-unit device identifier (stable across captures) |

The single-bit difference between `0x84` and `0x85` at offset 1 looks
like a state-change flag (e.g. "occupied" / "vacant" or sensor
in/out-of-range), but with only two samples the exact semantics
cannot be confirmed.

## Identity Hashing

```
identifier_hash = SHA256("smart_seat:{device_id_hex}")[:16]
```

The 5-byte device identifier (`8b 92 14 70 ef` in the captured sample)
is stable per unit, so it gives per-physical-seat granularity without
depending on the BLE MAC (which may rotate).

## What We Cannot Parse Without GATT

- Per-zone pressure-sensor readings
- Sitting duration
- Posture quality / alerts
- Battery percentage
- Live notifications

## References

- Bluetooth SIG company ID `0x04C5` (vendor not publicly documented)
- Survey of BLE smart-seat / posture-monitor products:
  - SmartSeat.eu: https://smartseat.eu/smart-office-chair/new-added-value
  - SitRight: http://www.sitright.io
  - Casana SmartSeat: https://casanacare.com/the-smartseat/
  - "Modular smart chair" study (BLE STM32WB55CGU6 implementation): https://pmc.ncbi.nlm.nih.gov/articles/PMC12252288/
