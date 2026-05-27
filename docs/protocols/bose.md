# Bose Audio Devices

## Overview

Bose audio devices (QuietComfort headphones, SoundLink speakers,
Frames sunglasses, etc.) advertise under company ID `0x0065` with a
short manufacturer-data payload. Two frame variants appear in
captures, distinguished by the first payload byte (frame type).

The exact byte-to-product mapping is not publicly documented; the
parser exposes the frame-type and product-code bytes verbatim so
downstream tooling (and future captures) can build a SKU mapping
over time.

> **Note on company ID**: `0x0065` is published in some Bluetooth-SIG
> mirrors as Hewlett-Packard Company. Bose's primary assignment is
> `0x009E`. The captures in adwatch's research export under `0x0065`
> were not corroborated with `0x009E` traffic, so attribution as
> "Bose" rests on legacy adwatch testing rather than a published SIG
> mapping. The parser also matches the Bose service UUID `0xFDF7`
> when present, which *is* SIG-assigned to Bose.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0065` | Disputed attribution — see note above |
| Service UUID | `FDF7` | Bose service (BT SIG, assigned to Bose Corp.) |
| Manufacturer data | 3 or 6 bytes after CID | Frame-type dispatched |

## Wire Format

### Type 1 — short status frame (3 bytes after CID)

```
65 00 | 01 c9 05
      └─┬─┘ └┬┘ └┬┘
       frame product state
       type   code  byte
```

| Offset (post-cid) | Bytes | Field |
|-------------------|-------|-------|
| 0                 | `01`  | frame_type — Type 1 status |
| 1                 | varies| product_code — Bose SKU identifier |
| 2                 | varies| state_byte — connection/playback state |

Observed captures: `01 c9 05` (1529 sightings), `01 c9 06` (404
sightings — same `product_code=0xc9`, state toggle), `01 c0 02`
(7 sightings — different product family).

### Type 2 — extended status frame (6 bytes after CID)

```
65 00 | 02 03 06 00 10 14
      └─┬─┘ └┬┘ └┬┘ └─┬─┘ └┬┘
       frame sub  product reserved state
       type  type code            byte
```

| Offset (post-cid) | Bytes | Field |
|-------------------|-------|-------|
| 0                 | `02`  | frame_type — Type 2 extended |
| 1                 | `03`  | sub_type (constant in captures) |
| 2                 | varies| product_code |
| 3–4               | `00 10` | reserved (constant) |
| 5                 | varies| state_byte |

Observed: `02 03 06 00 10 14` (261 sightings), `02 03 41 00 10 50`
(133 sightings — different product).

### FDF7 presence beacon (no manufacturer data)

Bose devices alternate the CID-0x0065 mfg frame above with a *second*
ad type carrying nothing but service-data on `0xFDF7`. The same
`deviceIdentifier` emits both back-to-back, so identity correlation is
unambiguous in real captures.

```
service_data["FDF7"] =
  01 <16 bytes rotating ID> 00 00 00 00 03
└┬┘                          └────┬────────┘
 frame                        trailing tail
 type                         (protocol version?)
```

| Offset | Bytes | Field |
|--------|-------|-------|
| 0      | `01`  | frame_type — version marker |
| 1–16   | varies | rotating identifier (changes between sightings of the same device) |
| 17–21  | `00 00 00 00 03` | trailing tail — constant across all captures |

The parser anchors on the *exact* 22-byte shape (length 22, leading
`0x01`, trailing `00 00 00 00 03`). Anything else on FDF7 — including
genuine HP printer-accessory frames (the SIG yaml lists FDF7 as
HP Inc., though Bose has been observed using it in practice) — is
rejected so we don't over-claim.

> **Why anchor strictly?** The SIG `member_uuids.yaml` attributes
> `0xFDF7` to *HP Inc.*, not Bose. In all of adwatch's research
> captures so far, the same physical device emits the CID-0x0065
> Bose mfg ad and the FDF7 22-byte body in lockstep, so we treat
> this body shape as Bose's. If HP accessory captures surface later
> with a different FDF7 body, they will fall through this anchor and
> remain available for a separate HP-specific parser.

## Identity Hashing

For Type 1 / Type 2 mfg frames:

```
identifier_hash = SHA256("{mac_address}:{product_code}")[:16]
```

For the FDF7 presence beacon (no product_code visible):

```
identifier_hash = SHA256("bose_fdf7:{mac_address}")[:16]
```

Combining MAC with product_code keeps per-unit granularity (two
QuietComfort 45 units would hash distinctly via MAC) while ignoring
the state byte (which toggles on connect/disconnect without
indicating a different device). The presence-beacon path falls back
to MAC alone because the rotating 16-byte body has no stable per-unit
component to anchor on.

## What We Cannot Parse Without GATT

- Battery percentage
- Currently-playing source (AAC / SBC / aptX)
- Active-noise-cancel level
- Bose Music app group membership
- Firmware version

All require a paired GATT session or Bose Music app integration.

## Captured Product Codes (May 2026 export)

| Frame | product_code | state_byte | Sightings | Inferred product |
|-------|--------------|------------|-----------|------------------|
| 0x01  | `0xC9`       | `0x05`     | 1,529     | Connected QC headphones (state=05) |
| 0x01  | `0xC9`       | `0x06`     | 404       | Same product, state=06 |
| 0x01  | `0xC0`       | `0x02`     | 7         | Different Bose product |
| 0x02  | `0x06`       | `0x14`     | 261       | Type-2 product 06 |
| 0x02  | `0x41`       | `0x50`     | 133       | Type-2 product 41 |

Counts are aggregated across all captures.

## References

- BT SIG company ID `0x009E` → Bose Corporation
- BT SIG 16-bit UUID `0xFDF7` → Bose Corporation (service)
- Bose Music app developer docs (not public): closed Bose SDK
