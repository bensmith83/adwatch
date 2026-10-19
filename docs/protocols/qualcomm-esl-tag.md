# Electronic Shelf Label Tag — Qualcomm FD05 Frame Family (ESL service 0x1857)

## Overview

Service data under Qualcomm Technologies' SIG member UUID `0xFD05` comes in
four frame shapes in our captures. Two are claimed by the parser:

- an **18-byte tag frame** (`06 c1` / `06 c0`), advertised together with the
  Bluetooth SIG **Electronic Shelf Label** service `0x1857` — a fleet of
  ~36 tags captured in one 32-minute window (2026-08-15, 64 records /
  417 sightings, −84..−102 dBm), and a handful more on two other days;
- a **19-byte config frame** (`05 e0 …`), byte-identical on every unit, with
  no service-UUID list at all — 62 records on three capture days, including
  34 stationary emitters seen for 62–100 minutes inside a US department store.

The tag fleet's shape — dozens of weak, one-day emitters, each with a
per-unit id and one of exactly two "group" values — is a store's shelf-label
fleet seen from an aisle. The config frame's role (access point, rail, or a
label in another mode) is not known.

**Attribution stops at the chip vendor.** `0xFD05` tells us the BLE
silicon / stack is Qualcomm's; the label maker (VusionGroup/SES-imagotag,
Hanshow, SoluM, Pricer, …) is NOT identified and is not claimed. The
ESL *class* is claimed for the tag frame on the strength of the SIG service
UUID: per the ESL Profile an ESL advertises `0x1857` while unassociated or
unsynchronised with its AP, which is also the only state in which a
passive scanner would see a fleet of them at all. A synchronised label
stops advertising and follows its AP's Periodic Advertising with Responses
(PAwR) train (encrypted commands, responses in assigned slots), which
phone BLE stacks do not surface — so a store whose labels are all in
sync shows no `0x1857` traffic at all.

## Identifiers

| Signal | Value | Notes |
|---|---|---|
| Service data key | `0xFD05` | Qualcomm Technologies, Inc. (SIG member UUID) — **required** |
| Service UUID | `0x1857` | SIG *Electronic Shelf Label* service — **required for the tag frame** |
| Service UUID | `0xFD05` | listed alongside `0x1857` by the tag frame |
| Service UUID | `0x18CF` | seen on the two unclaimed frame shapes; **not SIG-assigned** |
| Manufacturer data | *(absent)* | every FD05 frame |
| Local name | *(absent)* | every FD05 frame |
| Address type | `random` | did NOT rotate within a capture |

## Frame family

| Frame | Length | Advertised UUIDs | Records | Capture days | Parser |
|---|---|---|---|---|---|
| `06 c1` / `06 c0` + 12 B + 4 B group tag | 18 B | `1857`, `FD05` | 71 | 3 | tag frame |
| `05 e0` + 17 B | 19 B | *(none)* | 62 | 3 | config frame |
| `06 41` / `06 11` + 12 B + 4 B group tag | 18 B | `18CF`, `FD05` | 10 | 1 | not claimed |
| `03 00 10` | 3 B | `18CF`, `FD05` | 7 | 3 | not claimed |

Byte `[0]` reads as a frame type and byte `[1]` as flags in every shape.
On two capture days several kinds were first seen in the same second, which
is what ties them to one ecosystem.

## BLE Advertisement Format

### Tag frame — service data under `0xFD05` (18 bytes)

```
06 c1 30 xx xx xx 26 ca a9 5a 5d 60 bc c7 gg gg gg gg
│  │  │  └──┬───┘ └─────────┬───────┘ └────┬────┘
│  │  seq  tag id        opaque (8)      group tag (4)
│  flags
frame type
```

| Offset | Size | Field | Evidence |
|---|---|---|---|
| 0 | 1 | frame type `0x06` | constant (gated) |
| 1 | 1 | flags | `c1` ×69, `c0` ×2 — reported raw; bit 7 set on every `0x1857` frame |
| 2 | 1 | sequence | advances by exactly 1 per frame of a tag, roughly every 5 minutes |
| 3..5 | 3 | tag id | constant per tag; 43 distinct values over three capture days, none repeated across days |
| 6..13 | 8 | opaque | fresh on every sequence step, identical within a step (14 sightings of one payload) — a MIC / ciphertext |
| 14..17 | 4 | group tag | one of two values: `gggggggg`, `hhhhhhhh` |

The two group-tag values are **not specific to one site**: each turned up
on two different capture days, on different phones. The field looks
deployment- or vendor-wide (a key id, firmware or product class) rather
than an access-point or store id.

Real captures:

```
06c130xxxxxx26caa95a5d60bcc7gggggggg   38 sightings
06c131xxxxxxdac68e9139463f7fgggggggg   11 sightings — same tag, seq 0x30→0x31
06c1b9yyyyyy32352864c6b33e9dhhhhhhhh   14 sightings — other group
06c0d2zzzzzz530be0ce9dc04116hhhhhhhh    1 sighting  — flags 0xc0
```

One tag's five frames, with CoreBluetooth reporting the same peripheral
identifier throughout (the address held while the payload changed):

```
03:04  06c1 b7 yyyyyy 42fb5e5fa3354bee hhhhhhhh
03:09  06c1 b8 yyyyyy 734f1b3ce3e331b2 hhhhhhhh
03:10  06c1 b9 yyyyyy 32352864c6b33e9d hhhhhhhh
03:20  06c1 ba yyyyyy 4cbeef200b1ed443 hhhhhhhh
03:26  06c1 bb yyyyyy 1f8c6ef322f69b4f hhhhhhhh
```

#### Alternative reading (recorded, not adopted)

Bytes 2..5 could be a single little-endian 32-bit counter whose low byte
was all that moved in a 32-minute capture. The values (the 3-byte tag id
plus the sequence byte, read as one LE word) are not plausible uptimes or
Unix times, which is why the `[seq][3-byte id]` reading was adopted — but
if the counter reading is right, the "tag id" changes every 256 ticks
(~21 h at 5 min/tick) and the stable key with it. Across all captures,
17 tags were seen at more than one sequence value (largest span 4) and no
`ff → 00` wrap was observed, so the question is still open. A multi-day
capture of one tag settles it.

### Config frame — service data under `0xFD05` (19 bytes)

```
05 e0 01 e8 03 64 00 f4 01 c8 00 02 00 00 01 00 01 00 00
│  │  │  └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └──────┬───────┘
│  │  │   1000   100   500   200    2     00 01 00 01 00 00
│  │  01             (as little-endian 16-bit words — unproven)
│  flags
frame type
```

| Offset | Size | Field | Evidence |
|---|---|---|---|
| 0 | 1 | frame type `0x05` | constant (gated) |
| 1 | 1 | flags `0xE0` | constant (gated) |
| 2..18 | 17 | config | constant — reported raw |

- **The whole payload is `05e001e8036400f401c8000200000100010000` in all
  62 records**, on three capture days.
- No service-UUID list, no manufacturer data, no name.
- In the department store, 34 distinct addresses each held for 62–100
  minutes at −45..−100 dBm — fixed infrastructure, likely ceiling-mounted.
  No tag frames were seen on that visit, consistent with a fleet whose
  labels were all synchronised, or with labels that are not Bluetooth at all.
- On the two other days the frame was first seen in the same second as the
  tag frame or a `0x18CF` frame.

Read as LE16s the body holds 1000, 100, 500, 200, 2 — suspiciously round,
plausibly timing parameters in milliseconds. With nothing varying, that
reading cannot be tested, so the parser decodes none of it.

### `0x18CF` frames (not claimed)

- 18-byte `06 41` / `06 11` frames with UUIDs `0x18CF` + `0xFD05`: the tag
  frame's layout (10 records, 10 distinct ids at `[3..6)`, fresh 8 bytes,
  two group-tag values `iiiiiiii` ×6 / `jjjjjjjj` ×4), and flag bit 7
  clear where every `0x1857` frame has it set. Not claimed: `0x18CF` is not
  a SIG-assigned UUID, so the ESL claim does not carry over; the frames come
  from one site on one day with every tag seen once; and their group tags
  never match the `0x1857` tags' values, even at the same site and second.
- 3-byte `030010` with UUIDs `0x18CF` + `0xFD05`: constant, nothing to
  decode. Not claimed.

## Parser Scope (Passive Only)

**Tag frame** (`0x1857` required). Surfaces `frame_type`, `flags_hex`,
`sequence`, `tag_id_hex`, `opaque_hex`, `group_tag_hex`,
`esl_service_advertised`. Identity keys on the payload, not the address:

```
stable_key = qualcomm_esl_tag:<group tag hex>:<tag id hex>
identifier = SHA256(stable_key)[:16]
```

**Config frame** (19 bytes, `05 e0`, no service UUID other than FD05).
Surfaces `frame=config`, `frame_type`, `flags_hex`, `config_hex` (bytes
2..18 raw), `esl_service_advertised=false`. Every unit sends the same bytes,
so identity keys on the BLE address:

```
stable_key = qualcomm_esl_tag:mac:<address>
identifier = SHA256(stable_key)[:16]
```

Not decoded: what the tag frame's 8-byte field protects, what the group tag
indexes, what the config values mean, label size, displayed price, or the
label vendor.

## Detection Significance

A burst of tag frames is a retail floor using Bluetooth-standard ESLs whose
labels are not (yet) in sync with their access point — or a back room /
pallet of unprovisioned ones. Config-frame emitters show up as a few dozen
fixed points across a store even when no label is visible. All of it is
fixed infrastructure and of no tracking interest; the stable per-tag id is
expected (the store needs it).

## Confidence

- Tag frame structure: HIGH (71 records, 43 tags, consistent byte roles).
- Tag frame "electronic shelf label": HIGH (SIG service UUID is unambiguous).
- Config frame in the same Qualcomm FD05 family: HIGH (same member UUID,
  same type/flags layout, same-second co-location on two days).
- Config frame in the same ESL deployment as the tags: MEDIUM (~75%).
- Config frame role: UNKNOWN.
- Qualcomm silicon: HIGH (SIG member UUID).
- Label brand: NONE claimed.

## References

- [BT SIG `service_uuids.yaml`](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/service_uuids.yaml) — `0x1857 = Electronic Shelf Label`; no `0x18CF` entry (the list ends at `0x1860`)
- [BT SIG `member_uuids.yaml`](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — `0xFD05 = Qualcomm Technologies, Inc.`
- Bluetooth SIG, *Electronic Shelf Label Profile 1.0* (2023) — advertising
  requirements in the Unassociated / Unsynchronized states; PAwR for
  synchronised ESLs
- NearSight `research/sweep-2026-08-23-candidates.md` — tag-fleet cluster analysis
- NearSight research notes, 2026-10-18 — config frame and frame-family analysis
