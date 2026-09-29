# SRAM AXS (wireless bike components)

## Overview

SRAM's AXS ecosystem (eTap AXS derailleurs and shifters, Reverb AXS
dropper posts, AXS power meters) advertises over BLE for the AXS app.
Frames carry **dual independent vendor attribution**: SIG company ID
`0x0933` (SRAM) in the manufacturer data AND SIG member service UUID
`0xFE51` (also SRAM) in the advertised services.

First captured 2026-07-29 (four records, one passing bike); two more
frame variants captured 2026-08-13 (eight records, two devices); a
second long-frame extension shape captured 2026-08-24 (seven records,
two devices, variant b).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0933` (LE wire `33 09`) | SIG-assigned to SRAM |
| Service UUID | `0xFE51` | SIG member UUID, SRAM; co-advertised |
| Frame shape | one of three variants below | structural gate |

Either routing key can deliver the ad; the frame-shape guard is what
admits it.

### Byte Layout (manufacturer data incl. CID)

Three variants share the skeleton
`33 09 | <7 fixed bytes> | B | <3 fixed bytes> [| S] [| 13-byte TLV]`:

| Variant | Bytes [2..9) | Bytes [10..13) | Short/long length | Status byte |
|---------|--------------|----------------|-------------------|-------------|
| a (2026-07-29) | `00 00 01 01 00 04 05` | `1e 03 80` | 14 / 27 | yes ([13]) |
| b (2026-08-13) | `00 00 01 02 00 04 05` | `1f 03 80` | 14 / 27 | yes ([13]) |
| c (2026-08-13) | `00 00 01 01 60 fe 04` | `1f 03 00` | 13 / 26 | no |

* `B` (byte [9]) — slow counter or level: 0xc7/0xc9/0xca (variant a),
  0x4c→0x4d→0x4e across one minute (variant b), 0x95 (variant c).
  Battery percent is plausible for some variants but unproven.
* `S` — status byte: 0x50/0x51 (a), 0x64 (b).

### Long-frame extension, TLV shape (13 bytes; 27-byte frame)

```
01 01 09 | 0d 03 <5-byte system blob> XX 81 | 01
```

The middle nine bytes (`0d 03 … 81`) are **byte-identical to the FE51
service data co-advertised by the same device** — the manufacturer
frame embeds the service-data TLV verbatim. The 5-byte system blob is
stable per system (plausibly a pairing/system ID; surfaced as
`system_blob_hex`, not treated as a proven serial). Trailing pair
observed as `03 81` (a, b) and `04 81` (c).

### Long-frame extension, ASCII shape (14 bytes; 28-byte frame) — 2026-08-24

Both variant-b devices captured on 2026-08-23 (10:39 UTC, seven records)
sent their long frames with a **different, 14-byte** extension:

```
02 04 0a 02 | MM NN | 7 printable ASCII | 02
02 04 0a 02 | 37 01 | "gdef20d"          | 02      (one device, B = 0x4d/0x4f/0x51)
02 04 0a 02 | 36 00 | "gb7a7cd"          | 02      (other device, B = 0x49)
```

The seven characters are a git-describe style tag — `g` followed by six
hex digits — i.e. the component firmware's build hash, and `MM NN`
(`37 01` / `36 00`) reads naturally as a version pair (7.1 / 6.0). Both
readings are inferred; the app surfaces the bytes as
`extension_prefix_hex` and the characters as `extension_ascii_tag`
without asserting either meaning. The same devices also sent 14-byte
short frames, and one co-advertised the FE51 service data
`0d 03 c1 f5 fc 3c 32 04 81` (system blob `c1f5fc3c32`, trailing pair
`04 81`) — so the TLV and ASCII extension shapes coexist on one
firmware generation.

## Identity

Keyed on the BLE address. No proven per-device serial: the counter and
status bytes are low-cardinality and the system blob is shared across a
whole bike's component set.

## Parser Scope

Passive-only. The app parser (`sram_axs` v1.1, 2026-08-24) admits
variants **a and b** at 14, 27 and 28 bytes and surfaces `frame_variant`,
`counter_byte`, `status_byte`, `frame_size`, and for long frames
`extension_hex` plus either `system_blob_hex` (TLV shape) or
`extension_prefix_hex` + `extension_ascii_tag` (ASCII shape). Variant c
is documented above from the 2026-08-13 capture but is **not yet
admitted** — that capture is no longer in the merged corpus, so there is
no real fixture to pin it against; add it from the next variant-c
sighting. Which physical component emits which variant is unknown — a
bike passing at speed doesn't let the capture separate derailleur from
shifter from power meter.

## Confidence / Attribution

Vendor attribution **high** (dual registry allocations, consistent
across 12 records / 3+ devices / 3 scenes). Field semantics **medium**
(consistent within captures; counter/status readings unproven).
