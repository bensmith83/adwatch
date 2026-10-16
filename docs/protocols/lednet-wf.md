# Zengge LEDnetWF (WiFi+BLE LED Controllers)

## Overview

Zengge (Shenzhen Zengge Industries) ships the **LEDnetWF** product
line: WiFi+BLE dual-radio LED controllers and bulbs sold under
many sub-brands — Magic Home, Magic Hue, Zengge, SP-LED, BanlanX,
Surplife, and a long tail of Amazon white-label SKUs. SKUs cover
addressable strip controllers, RGB(W/CW) mini controllers, bulbs,
downlights, ceiling lights, ring lights, plant lights, even some
selfie lights and smart sockets/switches.

The BLE advertisement is rich: on the classic frames (byte 3 =
`0x01`/`0x02`) it carries the device MAC, product ID, firmware
version, and LED config version — enough to identify the specific
SKU even without a paired session. Live state (on/off, mode, RGB
values) is broadcast only on newer BLE-v5+ firmware variants; the
classic v1 frames leave the state region as static factory filler.
Our captures also hold a second firmware (byte 3 = `0x23`/`0x24`)
whose bytes 4–9 read as live state rather than a MAC (see below).

Distinct from `ELKBLEDOMParser`, which targets a completely
different cheap-strip-controller line (no manufacturer data,
GATT-only).

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Mfg-data | `00 5A xx …` / `01 5A xx …` | sta byte + Zengge BE company-id (low byte `4C`/`50`/`51`/`52`/`56`/`5B`) |
| LE company-id reading | `0x5A00` (sta=0x00) / `0x5A01` (sta=0x01) | Misleading — the device's CID is in BE at offset 1–2, not LE at 0–1 |
| Local name | `LEDnetWF<12 hex>` (or `LEDnetWF<digit><12 hex>` on newer FW) | The 12 hex chars are a stable device id (WiFi-side MAC or radio id) |

The leading byte is a **status byte (`sta`)**, not part of the
company-id — Zengge ships a non-conformant layout. Real Bluetooth
SIG manufacturer-data starts with a LE company-id; CoreBluetooth
reads bytes 0–1 LE which gives a fictional `0x5A00` (or `0x5A01`) here.

Primary LEDnetWF company-ids (BE-read of bytes 1–2):

| CID (BE) | Use |
|----------|-----|
| `0x5A4C` | Zengge product line (2026-10-07 sweep); every unit's svc-channel MAC is JM Zengge `08:65:F0` |
| `0x5A50` | LEDnetWF primary |
| `0x5A51` | LEDnetWF primary |
| `0x5A52` | LEDnetWF primary (seen in our captures); Bouffalo Lab svc-channel OUIs appear on this line only |
| `0x5A56` | svc-channel MAC `08:65:F0` (JM Zengge); 2 units (added 2026-10-16) |
| `0x5A5B` | svc-channel MAC `08:65:F0` (JM Zengge) or `E4:98:BB` (Phyplus Microelectronics); 2 units (added 2026-10-16) |

All six are decoded. Other low bytes on the same framing are seen
but not decoded: `0x63` (one svc-only unit whose "MAC" has the
multicast bit set), and `0x80` / `0x91` (only on the undecoded
sta=0x02 / key 0x5A02 sibling).

### `sta = 0x01` firmware reads as LE CID `0x5A01`

The 2026-10-07 nightly sweep found a second on-wire prefix: frames
starting `01 5a …` (`sta = 0x01`), which CoreBluetooth reads as LE
company id **0x5A01** (an unassigned SIG value — the same fictional-
CID artifact as `0x5A00`). v1.1 of the parser routes CID 0x5A01
alongside 0x5A00. On these frames the `ble_version` byte reads
`0x23`/`0x24`, but that is not specific to sta=0x01: sta=0x00
frames on 0x5A4C / 0x5A50 / 0x5A52 carry the same values. It looks
like a power state rather than a version — one unit flips between
`0x24` and `0x23` across days, like Magic Home's power-on/off codes.
The BE product ids seen (`0x0064` / `0x0060` / `0x0035` / `0x0006`)
are not fixed per unit on this firmware either (one 0x5A4C unit
reports both `0x0063` and `0x0064`), so they may be state too.

**Caution — bytes 4–9 are not a MAC on the `0x23`/`0x24` firmware:**
on these frames, on every line, bytes 4–9 are neither a MAC nor a
constant. They read `61:01:50:0f:00:00` on the 0x5A01-keyed 0x5A4C
units, `61:01:64:f0:b4:64` on a 0x5A00-keyed 0x5A4C unit, and the
same kind of block (`61:19:40:0f:00:00` etc.) on 0x5A50 / 0x5A52
frames whose byte 3 is `0x23`/`0x24`. The multicast bit is always
set, and on all 26 records that carry both channels the field never
equals the unit's svc-channel MAC. It reads as live state. The
parser reports it as `mfg_bytes_4_9_hex`; bytes 4–9 become
`device_mac` only when they are a unicast MAC, which in the corpus
means the classic byte-3 = `0x01`/`0x02` frames (Hong Kong Bouffalo
Lab `B4:E8:42` addresses). The unit's real factory MAC travels on
the service-data channel below.

## Wire Format ("Format A", 29 bytes)

```
00 | 5a 52 | 01 | 18 b9 05 xx xx xx | 00 33 | 1b | 09 | 01 02 03 04 05 06 07 08 09 a1 a2 a3 a4 a5 a6
└┬┘ └──┬─┘ └┬┘ └──────────┬───────┘ └──┬─┘ └┬┘ └┬┘ └─────────────────────┬──────────────────────────┘
 │     │    │             │            │    │   │                        └── state / RFU (live state on v5+ FW; filler on v1)
 │     │    │             │            │    │   └── led_version
 │     │    │             │            │    └── firmware_ver (low byte)
 │     │    │             │            └── product_id (BE)
 │     │    │             └── radio MAC (byte-3 0x01/0x02 frames only)
 │     │    └── ble_version (1 = legacy v1, no broadcast state)
 │     └── company_id (big-endian, NOT little-endian)
 └── sta status byte
```

| Offset | Bytes | Field | Notes |
|--------|-------|-------|-------|
| 0      | 1 | `sta` | Status byte (mode indicator; `0x00` or `0x01` in our captures, `0x02` on an undecoded sibling) |
| 1–2    | 2 | `company_id` (BE) | `0x5A52` etc. — Zengge LEDnetWF range |
| 3      | 1 | `ble_version` | Protocol version (1=legacy; ≥5 publishes state); `0x23`/`0x24` on a firmware where it behaves like a power state |
| 4–9    | 6 | `device_mac` / `mfg_bytes_4_9_hex` | Radio MAC when unicast (byte-3 `0x01`/`0x02` frames; last 3 bytes also appear in name suffix); otherwise a state block, reported as `mfg_bytes_4_9_hex` |
| 10–11  | 2 | `product_id` (BE) | See product table |
| 12     | 1 | `firmware_ver` | Low byte of firmware version |
| 13     | 1 | `led_version` | LED config version |
| 14–26  | 13 | `state_data` | Power / mode / RGB on v5+ FW; **factory filler on v1** |
| 27–28  | 2 | `rfu` | Reserved / unused |

The "state region" looks like an obvious counted sequence (`09 01
02 03 … a1 a2 a3 a4 a5 a6`) in our captures — that's coincidence,
not structure. On v1 firmware those bytes are uninitialized.

## Service-Data Channel (keys 0x5A00 / 0x5A01, 14 bytes) — v1.1

Units also broadcast a 14-byte service-data AD structure whose
16-bit key is the frame's own leading `sta 5a` bytes read LE:
`0x5A00` on sta=0x00 units, `0x5A01` on sta=0x01 units (the same
on-wire prefix the mfg channel leads with). The layout is identical
under both keys. A `0x5A02` key (the sta=0x02 sibling, same shape)
exists and is not decoded. The value mirrors the Format-A fields in
a different order and — critically — carries the unit's **real
factory MAC**:

```
4c 07 08 65 f0 ed 89 8b 00 35 1e 0a 05 00
└┬┘ └┬┘ └──────────┬───────┘ └┬┘ └─────┬──────┘
 │   │             │          │        └── opaque tail, 5 bytes (svc_tail_hex)
 │   │             │          │            (35 1e 0a 05 00 ×6 units,
 │   │             │          │             35 d4 0a 01 00 / b8 3b 09 01 00 /
 │   │             │          │             b6 1a 09 01 00 / 62 e0 04 01 00;
 │   │             │          │             semantics unconfirmed, reported raw)
 │   │             │          └── 0x00
 │   │             └── factory MAC (6 bytes, unicast)
 │   └── frame marker: 0x07 (0x06 on one batch of 0x52 units)
 └── cid-low byte (→ company_id BE 0x5A00|low)
```

| Offset | Bytes | Field | Notes |
|--------|-------|-------|-------|
| 0 | 1 | cid-low | `0x4C` / `0x50` / `0x52` / `0x56` / `0x5B` accepted → BE company id `0x5A00\|low`; `0x63` rejected |
| 1 | 1 | marker | `0x07`; `0x06` on one batch of 0x52 units |
| 2–7 | 6 | factory MAC | Must be unicast (I/G bit clear). OUI-verified: `08:65:F0` = **JM Zengge Co., Ltd** on every 0x4C / 0x50 / 0x56 unit and one 0x5B unit; Bouffalo Lab (Nanjing) OUIs (`B4:C2:E0`, `C8:90:A8`, …) on 0x52 units only — the BL602-class silicon; `E4:98:BB` = **Phyplus Microelectronics** on one 0x5B unit |
| 8 | 1 | zero | `0x00` |
| 9–13 | 5 | opaque tail | per-product-line values; reported as `svc_tail_hex`. Byte 13 is usually `0x00` but not always (`0x05` / `0x0d` / `0x27` / `0x03` on the 0x56 / 0x5B units) |

Records frequently carry **both** channels at once. When they do,
the svc cid-low byte equals the mfg cid_be low byte (all 26 such
records), and the svc MAC is reported as `device_mac` — metadata
only, not identity (see Identity Hashing); the mfg bytes 4–9 on
those frames are the state block described above. Full-history
evidence: the 0x5A4C / 0x5A01 family (2026-10-07 sweep) is 13
devices / 251 sightings / 2026-07-10 → 2026-10-06, 7 devices
advertising both channels; the 0x5A00-keyed channel is 20 records /
55 sightings / 16 devices, 2026-07-29 → 2026-10-11.

## Product-ID Lookup (selected — far from exhaustive)

Lifted from `8none1/lednetwf_ble/protocol_docs/`. Many SKUs not yet
catalogued; unknown product_ids still parse with `product_id_be`
surfaced verbatim.

| product_id | Family |
|------------|--------|
| `0x0033` | Ctrl_Mini_RGB |
| `0x0035` | Ctrl_Mini_RGBW |
| `0x0036` | Ctrl_Mini_RGBCW |
| `0x0053` | Bulb RGB |
| `0x0054` | Bulb RGBW |
| `0x0056` | Bulb RGBCW |
| `0x0062` | Strip RGB |
| `0x0063` | Strip RGBW |
| `0x0072` | Downlight RGBCW |
| `0x0097` | Ring light |
| `0x00A1` | Plant light |
| `0x00A2` | Selfie light |

## Local Name Decoding

```
LEDnetWF 0 0 0 0 3 3 X X X X X X
└──┬───┘ └─────────┬──────────┘
   │               └── 12-hex device id (WiFi/primary radio identifier)
   └────────────── Product-line prefix
```

Newer firmwares optionally insert a single digit between the
prefix and the hex (`LEDnetWF07AABBCCDDEEFF`) to expose the BLE
protocol version. The parser strips the optional digit when
extracting the suffix.

The **first 6 hex chars** of the suffix are typically a Zengge
vendor pseudo-OUI (`000033` is common — not a registered IEEE
OUI). The **last 6 hex chars** match the lower 3 bytes of the
radio MAC carried in the manufacturer data (on the classic byte-3 =
`0x01`/`0x02` frames, which carry one).

## Identity Hashing

```
identifier_hash = SHA256(name_suffix)[:16]       # every frame with an LEDnetWF name
identifier_hash = SHA256(ble_address)[:16]       # otherwise
```

Every frame keys the same way: the name suffix when the LEDnetWF
name is present (stable across MAC rotation for the classic
name-bearing bulbs), else the BLE address. There is no `stableKey`.

The svc-channel factory MAC (keys 0x5A00 / 0x5A01) is **not** an
identity seed; it is reported as `device_mac`, metadata only
(2026-10-16). Keying on it split real devices: some 0x5A52 lamps
alternate manufacturer-only frames and dual-channel frames from one
address, and a svc-first seed gave each lamp two identities. No svc
MAC has been seen under two addresses either, so the benefit across
address rotation is unproven. Address identity stands until a svc
MAC is seen surviving an address change.

## Captured Examples

```
LEDnetWF000033XXXXXX   mfr= 00 5a 52 01 18b905xxxxxx 0033 1b 09 010203040506070809 a1a2a3a4a5a6
                       → vendor=Zengge   ble_ver=1   product=Ctrl_Mini_RGB_0x33   fw=27
```

62 sightings across 2 instances in our test capture.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | CID range | Zengge |
| Company id (BE) | mfr[1..3] | Disambiguates LEDnetWF range |
| BLE protocol version | mfr[3] | 1=legacy, ≥5=broadcasts state; `0x23`/`0x24` looks like power state |
| Radio MAC (`device_mac`) | mfr[4..10], when unicast | Stable per unit; only on byte-3 = `0x01`/`0x02` frames |
| State block (`mfg_bytes_4_9_hex`) | mfr[4..10], when not unicast | The `0x23`/`0x24` firmware; not a MAC |
| Factory MAC (`device_mac`) | svc 0x5A00 / 0x5A01 [2..8) | Metadata only, not identity |
| Opaque tail (`svc_tail_hex`) | svc 0x5A00 / 0x5A01 [9..14) | Reported raw |
| Product family | mfr[10..12] | See lookup table; not fixed per unit on the `0x23`/`0x24` firmware |
| Firmware version (low byte) | mfr[12] | |
| LED config version | mfr[13] | |
| Name suffix (device id) | local name | Stable across MAC rotation |

## What Requires GATT Connection (or v5+ FW)

- Power on/off state
- Active scene / mode
- Current RGB / CCT values
- Brightness
- Scene speed / direction

On v5+ firmware, those fields appear in `state_data` (mfr[14..27])
without needing a connection — this parser doesn't decode them.
Our captures are no longer v1-only (the byte-3 = `0x23`/`0x24`
frames carry what looks like live state in bytes 4–9), but none
has been checked against the decoding rules in
`8none1/lednetwf_ble/protocol_docs/04_state_decoding.md` yet.

## References

- `8none1/lednetwf_ble` — canonical reverse-engineering and Home
  Assistant integration (`protocol_docs/02_manufacturer_data.md`,
  `protocol_docs/03_device_identification.md`)
- `8none1/zengge_lednetwf` — older sibling repo
- `rabidpaperclip/magichome2-ble` — sibling MagicHome2 BLE protocol
- Home Assistant `led_ble` integration (explicitly excludes
  LEDnetWF — different protocol)
