# PLAUD AI Recorder BLE Protocol

## Overview

PLAUD makes AI-powered voice recorders, including the PLAUD NOTE (card-style recorder) and PLAUD NotePin (wearable pin recorder). Both devices advertise via BLE for pairing with the PLAUD companion app. The advertisements contain manufacturer-specific data with device identification information.

## Identifiers

- **Local name pattern:** `PLAUD_NOTE`, `PLAUD NotePin` (prefix `PLAUD` followed by space or underscore)
- **Company IDs:** `0x0059` (PLAUD NOTE), `0x005D` (PLAUD NotePin) — these are Bluetooth SIG-assigned IDs for Qualcomm Technologies International and Plantronics respectively, likely inherited from the BLE chipset
- **Device class:** `recorder`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `PLAUD_NOTE` or `PLAUD NotePin` | Model identified by suffix |
| Company ID | 0x0059 or 0x005D | Varies by model, chipset-assigned |

### Manufacturer Data Structure

PLAUD devices send manufacturer-specific data with a TLV-like structure. Both models share a common tail pattern.

#### PLAUD NOTE Example (29 bytes)

```
59 00 02 78 03 04 56 5f 00 00 09 88 83 16 37 43
89 71 98 85 0a 00 04 f5 78 ed 1e 01 01
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0-1 | 2 | `59 00` | Company ID (0x0059, LE) |
| 2 | 1 | `02` | Unknown (possibly protocol version) |
| 3 | 1 | `78` | Unknown |
| 4-5 | 2 | `03 04` | Unknown |
| 6-19 | 14 | varies | Device-specific payload (likely includes serial/device ID) |
| 20-26 | 7 | `0a 00 04 XX XX XX XX` | Tail TLV: type=0x0A, length fields, 4 data bytes |
| 27-28 | 2 | `01 01` | Trailer (constant across both models) |

#### PLAUD NotePin Example (26 bytes)

```
5d 00 04 56 d5 00 00 08 88 00 04 01 22 73 62 61
44 0a 00 04 00 18 28 57 01 01
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0-1 | 2 | `5d 00` | Company ID (0x005D, LE) |
| 2 | 1 | `04` | Unknown (possibly protocol version) |
| 3-16 | 14 | varies | Device-specific payload |
| 17-23 | 7 | `0a 00 04 XX XX XX XX` | Tail TLV: type=0x0A, 4 data bytes |
| 24-25 | 2 | `01 01` | Trailer (constant) |

### Common Tail Pattern

Both models share the pattern `0a 00 04 [4 bytes] 01 01` at the end. The `0x0A` byte may be a TLV type indicator (possibly firmware version or status), and the trailing `01 01` appears to be a constant terminator or mode indicator.

### PLAUD NOTE Name-Only Advertisements

PLAUD NOTE also sends simpler advertisements with only the local name and no manufacturer data. These are likely connectable advertisements used for initial pairing discovery.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | local_name | PLAUD recorder nearby |
| Model | local_name suffix | NOTE vs NotePin |
| Device name | local_name | Full advertised name |
| Company ID | manufacturer_data[0:2] | Chipset-assigned BT SIG company ID |

## What We Cannot Parse (requires GATT connection)

- Battery level
- Recording status
- Storage capacity / usage
- Firmware version
- Transcription data

## Identity Hashing

```
identifier = SHA256("plaud:{mac}")[:16]
```

## Detection Significance

- PLAUD devices are AI voice recorders capable of recording and transcribing conversations
- The PLAUD NOTE is a card-sized device; the NotePin is a wearable pin
- Presence indicates active recording hardware nearby
- Both models advertise continuously when powered on, even when not actively recording

## Parsing Strategy

1. Match on local_name starting with `PLAUD` followed by space or underscore
2. Extract model name from local_name suffix (e.g., "NOTE", "NotePin")
3. If manufacturer data present, extract company ID
4. Return device class `recorder`

## References

- [PLAUD](https://www.plaud.ai/) — manufacturer website
- Bluetooth SIG Company Identifiers: 0x0059 (Qualcomm Technologies International), 0x005D (Plantronics)
