# Sonos Speakers

## Overview

Sonos speakers (Era, Beam, Arc, Move, Roam, One, Port, Sub, Ace
headphones, etc.) advertise continuously over BLE under company ID
`0x05A7` (Sonos, Inc., BT-SIG-assigned). The BLE radio is on
whenever the speaker is powered, so a single passive scan over a
home with Sonos hardware will pick up every device.

The advertisement is identification + presence only — live state
(volume, playback, group membership, queue) lives behind the Sonos
local API and requires either app pairing or the documented Sonos
HTTP API on the LAN.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x05A7` | Sonos, Inc. (BT SIG) |
| Local name | `S<NN> <XXXX> LE` | e.g. `S39 XXXX LE` — model code + 4-hex per-unit device suffix + `LE` mode marker |

## Wire Format

Long-form frames are **26 bytes after the CID** in real captures:

```
a7 05 | 06 00 12 [model_token] 2a 00 ca [feature_byte] 00 08 \
        00 00 00 00 00 00 00                                 \
        [6-byte device id] [3-byte family marker]
```

Field positions, byte offsets reckoned from the start of the
manufacturer-data payload (i.e. **after** the 2-byte CID):

| Offset (post-cid) | Bytes        | Field |
|-------------------|--------------|-------|
| 0                 | `06`         | header_byte (constant in captures) |
| 1                 | `00`         | reserved |
| 2                 | `12`         | reserved |
| 3 | varies | **model_token.** Not a product-family id. Real scans show the same model with different values (S38 seen as both `0x40` and `0x20`; S39 almost always `0x20` but once `0x00`; S19 seen as `0x00`). `0x10` appeared only on Amp (S16, 4 units) and Port (S23, 1 unit), the two models whose DoC product type is "Wireless Streaming Device" rather than "Wireless Smart Speaker". That is suggestive but rests on 5 units, so it is not decoded. |
| 4                 | `2A`         | constant |
| 5                 | `00`         | reserved |
| 6                 | `CA`         | constant |
| 7                 | varies       | feature_byte (`0x00` or `0x06` observed) |
| 8–16              | zeros        | padding / reserved |
| 17–22             | 6 bytes      | per-unit device identifier (MAC-like, stable per physical speaker) |
| 23–25 | 3 bytes | **family_marker.** The low two bytes are constant across units of one model in scans: 7 S57 units, 4 Amp units and 4 Era 100 units each share one value. Values differ between models. The low two bytes observed: `92 e9` Era 100 (S39), `92 eb` Era 300 (S41), `a8 e9` One SL (S22), `a8 ea` One SL (S38), `ac e9` Amp (S16), `a9 e9` Port (S23), `af e9` Arc (S19), `95 eb` S54, `85 e9` S57. The first byte was `0x33` in most frames and `0x30` in others, including both One SL codes and one Era 100 frame, so it looks like flags. The marker identifies the model line, but the model code in the local name already does that, and no mapping from marker to product is established. It is reported raw and never used to guess a product. |

The local-name model code is the authoritative product key. Use the manufacturer frame only when the name is absent, and even then do not guess a product from it.

A 17-byte short-form frame also appears (when the speaker has not
yet emitted its device-id tail) — the parser handles it gracefully
by extracting `model_token` and `feature_byte` while skipping
device-id fields.

## Local Name Decoding

```
"S39 XXXX LE"
 └┬┘ └─┬─┘ └┬┘
  │   │    └── BLE mode marker (constant)
  │   └────── 4-hex device suffix (per unit; redacted here)
  └────────── Sonos model code (see table below)
```

### Model code → product mapping

The `S<NN>` in the local name is Sonos's regulatory **Product Model Number**,
the same "Model: S__" printed on the product label. Every row below is quoted
from Sonos's own EU Declaration of Conformity for that product (index:
<https://www.sonos.com/en/support/policies>; PDFs under
`https://www.sonos.com/pdfs/conformity/`). Several products share one model
number. Sonos re-certifies variants under the existing number instead of
minting a new one.

| Model code | Product | Source (Sonos EU DoC) |
|------------|---------|------------------------|
| `S11` | Playbase | `playbase.pdf` |
| `S13` | One | `one-it.pdf` (lists S13 and S18 as "One") |
| `S14` | Beam | `beam.pdf`, `beam-it.pdf` |
| `S15` | Connect (ZonePlayer 90) | `connect.pdf` |
| `S16` | Amp | `amp.pdf` (product type "Wireless Streaming Device") |
| `S17` | Move | `move.pdf` |
| `S18` | One | `one.pdf`, `one-it.pdf` |
| `S19` | Arc | `arc.pdf` |
| `S22` | One SL | `one-sl-it.pdf` (lists S22 and S38 as "One SL") |
| `S23` | Port | `port.pdf` (product type "Wireless streaming Device") |
| `S24` | Five | `five.pdf` |
| `S26` | Sub | `sub.pdf` |
| `S27` | Roam (also Roam SL and Roam 2) | `roam.pdf` = `roam-sl.pdf` = `roam2.pdf` |
| `S36` | Ray | `ray.pdf` |
| `S37` | Sub Mini | `sub-mini.pdf` |
| `S38` | One SL | `one-sl.pdf` |
| `S39` | Era 100 (also Era 100 Pro and Era 100 SL) | `era-100.pdf`, `era-100-pro.pdf`, `era-100-sl.pdf` |
| `S41` | Era 300 | `era-300.pdf` |
| `S44` | Move 2 | `move2.pdf` |
| `S45` | Arc Ultra | `arc-ultra.pdf` |
| `S49` | Ace (headphones) | `ace.pdf` |
| `S51` | Amp Multi | `ampmulti.pdf` |
| `S52A` | Ace Ultra (headphones) | `ace-ultra.pdf` (BLE local-name form unconfirmed) |
| `S55` | Sub 4 | `sub4.pdf` ("SUB Gen 4") |
| `S58` | Play | `sonos-play.pdf` |
| `S59` | Beam Ultra | `beam-ultra.pdf` |

Corroboration for the older rows: the Sonos Community "Sonos and the FCC" list
compiled from FCC filings
(<https://en.community.sonos.com/advanced-setups-229000/sonos-and-the-fcc-6796981>)
agrees with every row it overlaps: S11, S13, S14, S15, S16, S17, S19, S22, S23,
S24, S26, S27 and S38.

**Seen in the wild but not verified:** `S54` and `S57`. Both appear in real
scans; S57 shows up on many distinct units. No DoC, FCC, press or community
source names them yet. The parser keeps the model code and claims no product.

**Removed from the old table** because Sonos's DoCs contradict them or nothing
verifies them: S1 "Play:5 (Gen 2)" (the Play:5 DoC says model S100), S2, S3,
S6, S9, S12, S15 "Port" (S15 is Connect), S16 "Move" (Amp), S17 "Arc" (Move),
S18 "Roam" (One), S23 "Roam SL" (Port), S27 "Ace" (Roam), S29 "Era 100" (Era
100 is S39), S30 "Era 300" (S41), S33 "Roam 2" (Roam 2 is S27), S39
"Era / Sub / Arc (gen)" (Era 100), and S43 (One SL revision, backed by a single
forum post only).

Unmapped codes still parse: `model_code` is kept verbatim and
`product` / `model_name` are left out.

## Identity Hashing

```
identifier_hash = SHA256(device_id_hex)[:16]    # when full frame
identifier_hash = SHA256(mac_address)[:16]      # short-form fallback
```

The 6-byte device_id is stable per physical unit and survives BLE
MAC rotation — making it a reliable per-speaker identity even when
the OS rotates the random address.

## Captured Examples

Frame shape only. Per-unit local-name suffixes are replaced with `XXXX` and
the 6-byte device id with `<device-id>`.

```
S39 XXXX LE   mfr=a705 06 00 12 20 2a 00 ca 00 00 08 00 00 00 00 00 00 00 <device-id> 3392e9
S38 XXXX LE   mfr=a705 06 00 12 40 2a 00 ca 00 00 08 00 00 00 00 00 00 00 <device-id> 33a8ea
S19 XXXX LE   mfr=a705 06 00 12 00 2a 00 ca 06 00 08 00 00 00 00 00 00 00 <device-id> 33afe9
```

The device id is per unit, so it is not published here.

## What We Cannot Parse Without GATT / LAN API

- Track / artist / album metadata (now-playing)
- Volume level
- Group / stereo-pair membership
- Network connectivity state
- Battery (Move / Roam only)
- Trueplay calibration state
- Audio input selection (Beam / Arc HDMI source)

All of those live in the Sonos local control API on the LAN, not the
BLE advertisement.

## References

- Sonos Community model number forum: https://en.community.sonos.com/components-and-architectural-228996/how-to-find-out-the-manufacture-date-of-my-sonos-components-6846597
- Sonos serial-number support: https://support.sonos.com/en-us/article/find-the-serial-number-and-pin-on-your-sonos-products
- BT SIG company ID `0x05A7` → Sonos, Inc.
