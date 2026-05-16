# JBL Speaker BLE Protocol

## Overview

JBL (owned by Harman International, a Samsung subsidiary) makes Bluetooth speakers and audio equipment. JBL speakers advertise via BLE using the assigned service UUID FDDF and local names starting with "JBL ". Some models also support Google's Find My Device Network (FMDN) via FE2C service data.

## Identifiers

- **Service UUID:** `FDDF` (16-bit, Bluetooth SIG assigned to Harman International)
- **Company ID:** `0x0ECB` (Harman International)
- **Local name pattern:** `JBL {model}` (e.g., `JBL PartyBox Stage 320`)
- **Device class:** `speaker`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `FDDF` (full: `0000fddf-0000-1000-8000-00805f9b34fb`) | Harman International |
| Local name | `JBL {model}` | Full product name |
| Company ID | `0x0ECB` | Present in some advertisement frames |

### Advertisement Frames

JBL speakers send multiple advertisement frame types:

#### Frame 1: Service UUID only
```
Service UUIDs: [FDDF, FE2C]
Service Data: {"FDDF": "", "FE2C": "1060c531a6a6861c21aa8f"}
Local name: JBL PartyBox Stage 320
```

#### Frame 2: Manufacturer data
```
Manufacturer data: cb0edd2001d06486a92401000068593259334901010000000000
Service Data: {"FDDF": ""}
Local name: JBL PartyBox Stage 320
```

### Manufacturer Data Structure (25 bytes)

```
cb 0e dd 20 01 d0 64 86 a9 24 01 00 00 68 59 32
59 33 49 01 01 00 00 00 00 00
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0-1 | 2 | `cb 0e` | Company ID (0x0ECB, LE) — Harman International |
| 2 | 1 | `dd` | Protocol identifier |
| 3 | 1 | `20` | Frame type / version |
| 4-24 | 21 | varies | Device-specific payload |

### FE2C Service Data (FMDN)

When present, FE2C service data indicates the speaker supports Google's Find My Device Network:

```
FE2C: 10 60 c5 31 a6 a6 86 1c 21 aa 8f
```

| Offset | Length | Description |
|--------|--------|-------------|
| 0 | 1 | FMDN frame type (0x10) |
| 1-10 | 10 | Ephemeral identifier for FMDN tracking |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid, service_data, or local_name | JBL speaker nearby |
| Model name | local_name (after "JBL ") | Full product model |
| FMDN support | FE2C service data presence | Google Find My Device enabled |
| Company ID | manufacturer_data[0:2] | Harman International (0x0ECB) |

### What We Cannot Parse (requires GATT connection)

- Battery level
- Volume level
- Active audio source
- Firmware version
- PartyBoost / Auracast group membership

## Sample Advertisements

```
JBL PartyBox Stage 320 (frame 1):
  Service UUIDs: FDDF, FE2C
  Service Data: {"FDDF": "", "FE2C": "1060c531a6a6861c21aa8f"}
  Sightings: 85

JBL PartyBox Stage 320 (frame 2):
  Manufacturer data: cb0edd2001d06486a92401000068593259334901010000000000
  Service Data: {"FDDF": ""}
  Sightings: 65
```

## Identity Hashing

```
identifier = SHA256("jbl:{mac}")[:16]
```

## Detection Significance

- Indicates a JBL Bluetooth speaker in the area
- PartyBox models are large, high-power party speakers
- FMDN support means the speaker can be located via Google's Find My Device network
- Always-on BLE when speaker is powered

## Parsing Strategy

1. Match on service UUID `FDDF` OR local_name matching `^JBL ` OR `fddf` key in service_data
2. Extract model name from local_name (everything after "JBL ")
3. Check for FE2C service data to flag FMDN support
4. Return device class `speaker`

## Legacy Wire Format (Harman CID 0x0057)

Older JBL speakers — JBL Charge 3 / Charge 4 / Flip 5 / Pulse 3 era,
manufactured before JBL's own SIG company-ID assignment `0x0ECB` —
advertise under the **parent Harman International** company ID
`0x0057` with a much shorter manufacturer-data block:

```
57 00 29 1f 04 00 39 ff       (real "JBL Charge 4" capture, 8 bytes)
└─┬─┘ └────────┬────────┘
 cid    6-byte payload
```

The 6-byte payload format is undocumented. The first byte appears to
be a frame-type indicator (`0x29` observed) and the trailing bytes
include what looks like flags + a per-device identifier. The local
name (`JBL <model>`) is the only reliable model identifier.

The parser tags these as `wire_format=harman_0057` (modern frames are
tagged `wire_format=jbl_ecb`) so downstream consumers can distinguish
the two protocol families.

## References

- [JBL](https://www.jbl.com/) — manufacturer website
- [Harman International](https://www.harman.com/) — parent company
- Bluetooth SIG 16-bit UUID assignment: FDDF = Harman International
- Bluetooth SIG Company ID: 0x0ECB = Harman International Industries, Inc.
- Bluetooth SIG Company ID: 0x0057 = Harman International (parent, used by legacy JBL Charge/Flip/Pulse era)
- [Google Find My Device Network](https://developers.google.com/find-my-device) — FMDN specification
