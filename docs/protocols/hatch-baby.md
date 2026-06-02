# Hatch Baby (Sound Machine / Night Light)

## Overview

Hatch Baby Rest sound machines and night lights broadcast BLE advertisements for control via the Hatch Sleep app. They are identified by their `local_name` (e.g. "Bedroom Hatch") and custom service UUIDs. Hatch devices use Nordic Semiconductor's BLE stack and include DFU (Device Firmware Update) capability.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | User-assigned name + " Hatch" or "Hatch Rest" | e.g. `Bedroom Hatch` |
| Service UUID (advertised) | `00001530-1212-efde-1523-785feabcd123` | Nordic DFU Service |
| Service UUID (advertised) | `02240001-5efd-47eb-9c1a-de53f7a2b232` | Hatch custom service |
| Service UUID (advertised) | `02260001-5efd-47eb-9c1a-de53f7a2b232` | Hatch custom service |

The Nordic DFU service UUID (`00001530-1212-efde-1523-785feabcd123`) is common to many Nordic-based IoT devices, but the combination with Hatch-specific UUIDs (`0224xxxx`, `0226xxxx`) is distinctive.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | local_name or service_uuids | Hatch device nearby |
| User-assigned name | local_name | e.g. "Bedroom" from "Bedroom Hatch" |
| Nordic DFU capable | service_uuid `00001530-...` | Firmware update support |

### What We Cannot Parse (requires GATT)

- Device model (Rest, Rest+, RestNoSD, etc.)
- Firmware version
- Hardware revision
- Battery level
- Current sound/light settings

## Local Name Pattern

Hatch devices use user-assigned names from the app, followed by " Hatch":

```
{room_name} Hatch
```

Examples: `Bedroom Hatch`, `Nursery Hatch`, `Living Room Hatch`

This means the local_name reveals room placement — useful for spatial context.

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

Hatch devices likely use a static or semi-static BLE MAC, making this a stable identifier.

## Known Models

| Model | Product | Notes |
|-------|---------|-------|
| RestNoSD | Hatch Rest (no SD card) | Original sound machine |
| Rest+ | Hatch Rest+ | WiFi + BLE model |
| Rest 2nd Gen | Hatch Rest 2nd Gen | Latest generation |

## Detection Significance

- Baby/child monitoring device — strong indicator of a nursery or family environment
- User-assigned name reveals room placement
- Broadcasts continuously for app control (always-on BLE)
- Nordic DFU service indicates OTA firmware update capability

## Manufacturer Data: the "RTj" frame

When the device advertises with manufacturer data (CID `0x0434`, Hatch Baby
Inc.), the 24-byte payload uses a fixed TLV-style skeleton whose ASCII
section markers spell `RTj … C … S … E … P … e …`:

```
offset:  0  1  2 | 3  4  5 | 6 | 7  8  9 10 | 11 | 12 13 | 14 | 15 16 17 18 19 | 20 | 21 | 22 | 23
bytes:   R  T  j | <seq24LE> | C |  state-C  |  S | prg-S |  E |  zero  padding | P  | ?  |  e | ?
```

| Field | Offset | Length | Notes |
|-------|--------|--------|-------|
| Magic | 0 | 3 | ASCII `"RTj"` — protocol marker |
| `seq_le24` | 3 | 3 | 24-bit little-endian sequence counter; increments per advertisement |
| `'C'` marker | 6 | 1 | section delimiter (`0x43`) |
| `state_c_hex` | 7 | 4 | per-unit state block; stable for a given unit while idle (e.g. `EE 76 74 0C` for Bedroom Hatch, `23 FF 27 0F` for Colin's). Sentinel `FF FF FF FF` observed on units in their default/unprovisioned state. |
| `'S'` marker | 11 | 1 | section delimiter (`0x53`) |
| `program_s_hex` | 12 | 2 | program / scene bytes; varies per unit and per chosen scene |
| `'E'` marker | 14 | 1 | section delimiter (`0x45`) |
| zero pad | 15 | 5 | always `00 00 00 00 00` |
| `'P'` marker | 20 | 1 | section delimiter (`0x50`) |
| `aux_p_hex` | 21 | 1 | unknown auxiliary byte (varies per unit; e.g. `0x03` Bedroom, `0xDF` Colin, `0x1F` Maia) |
| `'e'` marker | 22 | 1 | section delimiter (`0x65`) |
| `aux_e_hex` | 23 | 1 | unknown auxiliary byte (`0x00` for most units, `0x82` seen on Maia) |

The parser sets `frame_valid: "true"` when the magic and all five section
markers line up, `"false"` otherwise — so downstream consumers can rely on
the structured fields when `frame_valid` is true and fall back to raw
`payload_hex` when it's false.

### Captured example payloads (mfr-data after the 2-byte CID)

```
Bedroom Hatch: 52546A13 5F70 43 EE76740C 53 045D 45 0000000000 50 03 65 00
Colin’s Hatch: 52546A13 2776 43 23FF270F 53 064F 45 0000000000 50 DF 65 00
Maia:          52546A13 5F60 43 FFFFFFFF 53 0351 45 0000000000 50 1F 65 82
Lucas's Room:  52546A01 E860 43 EB8E487F 53 0333 45 0000000000 50 02 65 00
```

`state_c_hex` and `program_s_hex` together act as a per-unit fingerprint
when the device is idle, which lets us tell apart multiple Hatches without
relying on the user-assigned local name.

## Local Name Patterns

Beyond the documented `"<Room> Hatch"` convention, Hatch units in the wild
can be renamed to **any free-form label** (e.g. `Maia`, `Lucas's Room`).
The parser surfaces:

- `room_name` when the local name ends in `" Hatch"` (e.g. `"Bedroom"` from
  `"Bedroom Hatch"`).
- `device_label` when the local name is something other than the bare
  `"Hatch"` and does not end in `" Hatch"` — preserving custom labels for
  display.

## Future Work

- Confirm the semantics of the `program_s_hex` 2-byte field (program ID +
  scene? brightness + colour temp?) by correlating with app-side state
  changes.
- Decode the `aux_p_hex` byte — possibly an audio-volume or sound-program
  byte (varies broadly across units).
- Identify why one unit broadcasts `state_c_hex = FF FF FF FF` (default /
  unprovisioned state vs. a different product variant).

## 2nd-Generation Rest line ("RIoT", ESP32-based)

The **Hatch Rest 2nd Gen** (`riot`, retail SKU HBR4400) and **Hatch Rest+
2nd Gen** (`riotPlus`, retail SKU HBR4600) replaced the original Nordic
chipset with an **Espressif ESP32-WROVER-E** module (FCC filings
`2AFYZ-HBREST2` and `2AFYZ-HBRESTPLUS2`, both Aug 2021). Hatch's internal
codename for the platform is **"RIoT"** (Rest IoT). Day-to-day control
runs over AWS-IoT MQTT (cloud); BLE is reserved for provisioning and a
short startup advertising window.

Ground-truth capture (export 16, 2026-06-02) of a Rest+ 2nd Gen during
boot, verified via nRF Connect GATT-read of the Device Information
Service (0x180A):

| DIS characteristic | Value |
|--------------------|-------|
| Manufacturer Name (0x2A29) | `Hatch Baby` |
| Model Number (0x2A24) | `RIOT Plus` |
| Serial Number (0x2A25) | `90380C9ACDE6` (matches device WiFi MAC) |
| Hardware Revision (0x2A27) | `8.0.0` |
| Firmware Revision (0x2A26) | `7.1.622` |

### RIOT frame format

The 2nd-gen Rest still advertises under **CID `0x0434` (Hatch Baby)** —
same vendor ID as the 1st gen — but with a totally different payload:

```
offset:  0  1 | 2 3 4 5 6 7 8 9
bytes:   E  M | <8-byte stable per-unit cookie>
```

| Field | Offset | Length | Notes |
|-------|--------|--------|-------|
| Magic | 0 | 2 | ASCII `"EM"` (`0x45 0x4D`) — RIoT protocol marker |
| Unit cookie | 2 | 8 | per-unit identifier, **stable** across captures — no counter, no sequence |

Example captured payload (from the Rest+ 2nd Gen with serial
`90380C9ACDE6`):

```
RIOT Plus: 45 4D D2 59 6E E3 85 A4 5A 01
```

The local-name advertises the model and the trailing 6 hex chars of the
device's serial / WiFi MAC:

| Local name | Model | mac_suffix |
|------------|-------|------------|
| `RIOT Plus9ACDE6` | Rest+ 2nd Gen | `9ACDE6` |
| `RIOT <6hex>` (extrapolated) | Rest 2nd Gen | (lower 24 bits of serial) |

The advertisement also includes the standard SIG service UUID
`180A` (Device Information) and service data on `180F` carrying the
battery percentage.

### Parser fields for the 2nd-gen Rest

| Field | Source | Notes |
|-------|--------|-------|
| `frame_type` | `"riot"` | distinguishes RIoT from the 1st-gen RTj frame |
| `frame_valid` | `"true"` | when the "EM" magic + ≥10-byte payload align |
| `product_code` | name-derived | `riotPlus` for Rest+ 2nd Gen, `riot` for Rest 2nd Gen |
| `product_name` | name-derived | `Hatch Rest+ 2nd Gen` / `Hatch Rest 2nd Gen` |
| `mac_suffix` | last 6 hex of local name | last 24 bits of the device's serial / WiFi MAC |
| `riot_unit_cookie_hex` | mfr bytes 2–9 | 8-byte stable per-unit identifier |
| `battery` | service data `180F` | battery percentage (same as 1st-gen) |

### Operating-mode caveat

The Rest 2/Rest+ 2 only broadcasts the RIoT frame **during a ~2 minute
window after power-on** while it brings up WiFi. Once it has joined the
home WiFi, BLE advertising stops entirely (the device is then controlled
exclusively over AWS-IoT MQTT). A persistent BLE scanner will *only* see
the device during boot — unplug/replug it to re-trigger the window.

## References

- [Hatch Sleep](https://www.hatch.co/) — manufacturer website
