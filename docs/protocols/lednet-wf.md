# Zengge LEDnetWF (WiFi+BLE LED Controllers)

## Overview

Zengge (Shenzhen Zengge Industries) ships the **LEDnetWF** product
line: WiFi+BLE dual-radio LED controllers and bulbs sold under
many sub-brands — Magic Home, Magic Hue, Zengge, SP-LED, BanlanX,
Surplife, and a long tail of Amazon white-label SKUs. SKUs cover
addressable strip controllers, RGB(W/CW) mini controllers, bulbs,
downlights, ceiling lights, ring lights, plant lights, even some
selfie lights and smart sockets/switches.

The BLE advertisement is rich: it carries the device MAC, product
ID, firmware version, and LED config version — enough to identify
the specific SKU even without a paired session. Live state
(on/off, mode, RGB values) is broadcast only on newer BLE-v5+
firmware variants; legacy v1 firmware (what we see here) leaves
the state region as static factory filler.

Distinct from `ELKBLEDOMParser`, which targets a completely
different cheap-strip-controller line (no manufacturer data,
GATT-only).

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Mfg-data | `00 5A 5{0,1,2} …` | sta=0 + Zengge BE company-id |
| LE company-id reading | `0x5A00` | Misleading — the device's CID is in BE at offset 1–2, not LE at 0–1 |
| Local name | `LEDnetWF<12 hex>` (or `LEDnetWF<digit><12 hex>` on newer FW) | The 12 hex chars are a stable device id (WiFi-side MAC or radio id) |

The leading byte is a **status byte (`sta`)**, not part of the
company-id — Zengge ships a non-conformant layout. Real Bluetooth
SIG manufacturer-data starts with a LE company-id; CoreBluetooth
reads bytes 0–1 LE which gives a fictional `0x5A00` here.

Primary LEDnetWF company-ids (BE-read of bytes 1–2):

| CID (BE) | Use |
|----------|-----|
| `0x5A4C` | Bouffalo-silicon product line (2026-10-07 sweep; svc-channel MACs verify) |
| `0x5A50` | LEDnetWF primary |
| `0x5A51` | LEDnetWF primary |
| `0x5A52` | LEDnetWF primary (seen in our captures) |

Other Zengge sub-lines use `0x5A20`–`0x5A4F`; we don't route
them to this parser.

### `sta = 0x01` firmware reads as LE CID `0x5A01`

The 2026-10-07 nightly sweep found a second on-wire prefix: frames
starting `01 5a …` (`sta = 0x01`), which CoreBluetooth reads as LE
company id **0x5A01** (an unassigned SIG value — the same fictional-
CID artifact as `0x5A00`). v1.1 of the parser routes CID 0x5A01
alongside 0x5A00. On this firmware the `ble_version` byte runs
`0x23`/`0x24` and the BE product ids seen are `0x0064` / `0x0060` /
`0x0035` / `0x0006`.

**Caution — placeholder MAC field on the 0x5A4C line:** bytes 4–9
read `61:01:50:0f:00:00` (and `61:19:40:0f:00:00` etc.) — identical
across every unit of the product line, trailing zeros, unassigned
OUI. It is **not** a per-unit MAC; decode it for forensics but never
key identity on it. The unit's real factory MAC travels on the
service-data channel below.

## Wire Format ("Format A", 29 bytes)

```
00 | 5a 52 | 01 | 18 b9 05 c6 0e 3f | 00 33 | 1b | 09 | 01 02 03 04 05 06 07 08 09 a1 a2 a3 a4 a5 a6
└┬┘ └──┬─┘ └┬┘ └──────────┬───────┘ └──┬─┘ └┬┘ └┬┘ └─────────────────────┬──────────────────────────┘
 │     │    │             │            │    │   │                        └── state / RFU (live state on v5+ FW; filler on v1)
 │     │    │             │            │    │   └── led_version
 │     │    │             │            │    └── firmware_ver (low byte)
 │     │    │             │            └── product_id (BE)
 │     │    │             └── radio MAC
 │     │    └── ble_version (1 = legacy v1, no broadcast state)
 │     └── company_id (big-endian, NOT little-endian)
 └── sta status byte
```

| Offset | Bytes | Field | Notes |
|--------|-------|-------|-------|
| 0      | 1 | `sta` | Status byte (mode indicator; 0 in our captures) |
| 1–2    | 2 | `company_id` (BE) | `0x5A52` etc. — Zengge LEDnetWF range |
| 3      | 1 | `ble_version` | Protocol version (1=legacy; ≥5 publishes state) |
| 4–9    | 6 | `mac_address` | Radio MAC (last 3 bytes also appear in name suffix) |
| 10–11  | 2 | `product_id` (BE) | See product table |
| 12     | 1 | `firmware_ver` | Low byte of firmware version |
| 13     | 1 | `led_version` | LED config version |
| 14–26  | 13 | `state_data` | Power / mode / RGB on v5+ FW; **factory filler on v1** |
| 27–28  | 2 | `rfu` | Reserved / unused |

The "state region" looks like an obvious counted sequence (`09 01
02 03 … a1 a2 a3 a4 a5 a6`) in our captures — that's coincidence,
not structure. On v1 firmware those bytes are uninitialized.

## Service-Data Channel (key 0x5A01, 14 bytes) — v1.1

The `sta = 0x01` units also broadcast a service-data AD structure
keyed `0x5A01` (the same on-wire `01 5a` prefix the mfg channel
leads with). The value mirrors the Format-A fields in a different
order and — critically — carries the unit's **real factory MAC**:

```
4c 07 08 65 f0 ed 89 8b 00 35 1e 0a 05 00
└┬┘ └┬┘ └──────────┬───────┘ └┬┘ └───┬───┘ └┬┘
 │   │             │          │      │       └── 0x00
 │   │             │          │      └── opaque per-firmware word
 │   │             │          │         (35 1e 0a 05 ×6 units,
 │   │             │          │          35 d4 0a 01 / b8 3b 09 01 /
 │   │             │          │          b6 1a 09 01 — semantics
 │   │             │          │          unconfirmed, reported raw)
 │   │             │          └── 0x00
 │   │             └── factory MAC (6 bytes)
 │   └── 0x07 frame marker (constant on all captures)
 └── cid-low byte (0x4C/0x50/0x52 → company_id BE 0x5A00|low)
```

| Offset | Bytes | Field | Notes |
|--------|-------|-------|-------|
| 0 | 1 | cid-low | `0x4C` / `0x50` / `0x52` → BE company id `0x5A00\|low` |
| 1 | 1 | marker | `0x07` constant |
| 2–7 | 6 | factory MAC | OUI-verified: `08:65:F0` = **JM Zengge Co., Ltd**; `B4:C2:E0` / `C8:90:A8` = **Bouffalo Lab (Nanjing)** — the BL602-class silicon |
| 8 | 1 | zero | `0x00` |
| 9–12 | 4 | opaque word | per-product-line constants; reported as `svc_tail_hex` |
| 13 | 1 | zero | `0x00` |

Records frequently carry **both** channels at once. When they do,
the svc MAC is the identity anchor (the mfg MAC field is the
placeholder described above). Full-history evidence (2026-10-07
sweep): 13 devices / 251 sightings / 2026-07-10 → 2026-10-06, 7
devices advertising both channels.

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
LEDnetWF 0 0 0 0 3 3 C 6 0 E 3 F
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
radio MAC carried in the manufacturer data.

## Identity Hashing

```
identifier_hash = SHA256(svc factory MAC)[:16]   # v1.1 — preferred when the 0x5A01 svc channel is present
identifier_hash = SHA256(name_suffix)[:16]       # stable — classic name-bearing bulbs
identifier_hash = SHA256(mac_address)[:16]       # fallback when neither is present
```

The svc-channel factory MAC is preferred because it is the unit's
real radio identifier and survives the BLE address rotation these
controllers do; the name suffix is equally durable for the classic
LEDnetWF-named bulbs (which never carry the svc channel); falling
back to the BLE MAC loses identity if the device rotates.

## Captured Examples

```
LEDnetWF000033C60E3F   mfr= 00 5a 52 01 18b905c60e3f 0033 1b 09 010203040506070809 a1a2a3a4a5a6
                       → vendor=Zengge   ble_ver=1   product=Ctrl_Mini_RGB_0x33   fw=27
```

62 sightings across 2 instances in our test capture.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | CID range | Zengge |
| Company id (BE) | mfr[1..3] | Disambiguates LEDnetWF range |
| BLE protocol version | mfr[3] | 1=legacy, ≥5=broadcasts state |
| Radio MAC | mfr[4..10] | Stable per unit |
| Product family | mfr[10..12] | See lookup table |
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
without needing a connection — this parser doesn't decode them
yet because our captures only contain v1 devices. Decoding rules
in `8none1/lednetwf_ble/protocol_docs/04_state_decoding.md` when
v5+ samples become available.

## References

- `8none1/lednetwf_ble` — canonical reverse-engineering and Home
  Assistant integration (`protocol_docs/02_manufacturer_data.md`,
  `protocol_docs/03_device_identification.md`)
- `8none1/zengge_lednetwf` — older sibling repo
- `rabidpaperclip/magichome2-ble` — sibling MagicHome2 BLE protocol
- Home Assistant `led_ble` integration (explicitly excludes
  LEDnetWF — different protocol)
