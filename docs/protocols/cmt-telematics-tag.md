# Cambridge Mobile Telematics Tag (service data 0xB10D, embedded factory MAC)

## Overview

[Cambridge Mobile Telematics](https://www.cmtelematics.com/) (CMT) supplies
the telematics behind many usage-based car-insurance programs. Its hardware
product is the **DriveWell Tag**, a small windshield-mounted BLE tag that
pairs with the insurer's phone app to attribute trips to a specific car
and to sharpen crash and phone-handling detection.

The tag advertises a fixed 12-byte frame in service data under the non-SIG
16-bit UUID `0xB10D`. The frame's only varying field is a 6-byte value that
resolves in the IEEE MA-L registry to **Cambridge Mobile Telematics, Inc.**
— on two different CMT blocks across the three units captured — so it is
the tag's factory MAC, broadcast in the clear while the BLE address it
advertises from rotates.

Captured in the 2026-08-24 → 2026-08-26 telemetry sweeps (three units, one
household scene — parked cars), attributed and shipped on 2026-08-27. The
2026-08-01 and 2026-08-25 sweeps had parked the cluster on the watchlist as
"MAC-shaped but no registered OUI"; that lookup was wrong.

## Supported Models

| Model | Attribution | Notes |
|-------|-------------|-------|
| DriveWell Tag | probable | CMT's only BLE hardware product; the frame is not documented by CMT, so the product name is inferred from the vendor, not decoded from the bytes |

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service data | under `0xB10D` | exactly 12 bytes |
| Service UUID (16-bit list) | `0xB10D` | advertised alongside |
| Company ID | none | no manufacturer-specific data |
| Local name | none | |
| Address | random | rotates across captures; the embedded MAC does not |
| Embedded OUI | `0C:C8:44`, `78:49:46` observed | IEEE MA-L → Cambridge Mobile Telematics, Inc. CMT also holds `4C:B8:2C` and `BC:86:A5` |

`0xB10D` is not a Bluetooth SIG allocation. The vendor attribution rests on
the IEEE registration of the embedded MAC — two independent CMT blocks on
three units, which is the corroboration a single matching prefix would
lack.

### Frame layout (service data, 12 bytes)

| Offset | Field | Size | Observed | Notes |
|--------|-------|------|----------|-------|
| 0–3 | header | 4 | `33 3e 15 dd` | constant across all three units; meaning unknown, reported raw and **not** gated on |
| 4–9 | factory MAC | 6 | `0c c8 44 …` (×2 units), `78 49 46 …` (×1) | IEEE MA-L block registered to CMT; the tag's permanent hardware address |
| 10–11 | trailer | 2 | `02 00` | constant across all three units; reported raw |

### Examples (real header/trailer and OUIs; NIC bytes withheld)

```
33 3e 15 dd | 0c c8 44 xx xx xx | 02 00     unit A (2026-08-24 21:01 UTC)
33 3e 15 dd | 78 49 46 xx xx xx | 02 00     unit B (2026-08-24 13:37 UTC)
33 3e 15 dd | 0c c8 44 xx xx xx | 02 00     unit C (2026-08-26 20:59 UTC)
header        factory MAC         trailer
```

## Parser Scope (passive-only)

`cmt_telematics_tag` claims an advertisement when `0xB10D` service data is
exactly 12 bytes **and** bytes 4–6 are one of CMT's IEEE MA-L blocks
(`OUIVendorLookup`). A `0xB10D` frame carrying any other OUI stays
unclaimed — the UUID alone is not evidence of the vendor. It reports:

| Field | Source |
|-------|--------|
| `vendor` | `Cambridge Mobile Telematics, Inc.` |
| `product` | `DriveWell Tag (probable)` |
| `service_uuid` | `b10d` |
| `embedded_mac` | bytes 4–9 as `xx:xx:xx:xx:xx:xx` — tagged **unique, stable** |
| `oui`, `oui_vendor` | the MAC's first three bytes and their registry owner |
| `header_hex`, `trailer_hex` | bytes 0–3 and 10–11, raw |
| `payload_hex` | the whole frame |
| `attribution_note`, `embedded_mac_note` | the reasoning above, in the record |

Identity is keyed on the embedded MAC (`stableKey = cmt_telematics_tag:<mac>`),
which is what survives the random-address rotation. Device class
`vehicle_telematics`.

## Privacy

Each tag pays the cost of BLE address privacy and then defeats it by
broadcasting its permanent factory MAC. Because the tag lives in one car,
a stable tag identity is a stable **car** identity: anyone listening can
tell when a specific insured vehicle is nearby, across days, without any
insurer data. That is the finding worth flagging to anyone auditing a
usage-based-insurance deployment, and it is why the parser keys identity on
the MAC rather than pretending the address rotation helps.

## What We Cannot Parse

- The header word `33 3e 15 dd` and trailer `02 00`: constant across three
  units on one install. A protocol/frame id and a version are plausible
  readings; a per-program or per-firmware value is equally plausible, which
  is why neither is gated on.
- Which insurer program the tag belongs to, whether it is currently paired,
  battery state, or any trip data — none of that is in the frame.
- Confirmation that the product is the DriveWell Tag specifically rather
  than an OEM variant; CMT publishes no BLE documentation.

## References

- NearSight `research/sweep-2026-08-27-candidates.md` — the three-unit
  capture and the corrected OUI lookup
- NearSight `research/sweep-2026-08-01-candidates.md`,
  `research/sweep-2026-08-25-candidates.md` (branch `sweep/2026-08-25`) —
  the earlier watchlist entries
- IEEE MA-L registry (standards-oui.ieee.org) — `0C-C8-44`, `4C-B8-2C`,
  `78-49-46`, `BC-86-A5` → Cambridge Mobile Telematics, Inc. (via
  `src/adwatch/_oui_vendors.py`)
- [Bluetooth SIG member service UUIDs](https://bitbucket.org/bluetooth-SIG/public/raw/HEAD/assigned_numbers/uuids/member_uuids.yaml) — `0xB10D` not assigned
- Cambridge Mobile Telematics — DriveWell Tag product page (windshield BLE
  tag for usage-based insurance)
