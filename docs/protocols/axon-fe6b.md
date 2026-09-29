# Axon FE6B (body-worn / fleet hardware)

## Overview

Axon Enterprise (formerly TASER International) holds the Bluetooth SIG
**member service UUID `0xFE6B`** ("TASER International, Inc."). Devices
from Axon's law-enforcement side — body cameras (Body 3/4), in-car /
fleet systems, Signal sidearm sensors — broadcast an 18- or 23-byte
service-data frame under that UUID. The UUID allocation itself is the
vendor attribution; a passive capture cannot pin which product is
which, so the parser claims the vendor and the wire shape, not a model.

This is distinct from the consumer TASER protocol (see `taser.md`):
those devices advertise a `TASER` GAP name, the Axon OUI and a
proprietary 128-bit GATT UUID family, and never this FE6B service data.

First capture: 2026-08-08, nine records from five distinct
random-address devices inside one two-minute window — a passing
law-enforcement encounter (the same window also contained a consumer
TASER CID 0x034D frame and two `METROPOLISDEVICE` ASCII-UUID beacons).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service data UUID | `0xFE6B` | SIG member UUID, TASER International, Inc. |
| Length | 18 (v1) or 23 (v2) bytes | exact-length gate |
| Byte [0] | `0x01` (v1) / `0x02` (v2) | version/format byte |

### Byte Layout — v1 (18 bytes, 8 of 9 observed records)

```
Offset  Size  Field
------  ----  -----
0       1     Version (0x01)
1       1     Frame/device type code (0x01 and 0x02 observed)
2–9     8     Unit ID — fixed per device across sightings and counter
              changes, distinct across devices
10–11   2     Counter, uint16 LE — increments between sightings of one
              unit (0x0bdd→0x0be9 on one unit, 0x0064→0x007c on another)
12–13   2     0x00 0x00 (constant in all records; reported raw)
14–16   3     Per-unit constant (reported raw, uninterpreted)
17      1     Terminator 0x03 (constant; gated on)
```

### Byte Layout — v2 (23 bytes, 1 observed record)

Fields [1..14) exactly as v1; bytes [14..23) are a **9-byte
printable-ASCII serial** replacing the v1 tail + terminator. Observed:
`X60AE544A` — Axon's documented X-prefix serial convention (compare the
consumer Pulse+ GATT-trace serial `X87004693`). The parser requires the
serial region to be printable ASCII before claiming a v2 frame.

## Identity

Every observed unit advertises from a random rotating BLE address while
the embedded unit ID never changes, so device identity anchors on the
unit ID (`stableKey = axon_fe6b:<unit id hex>`; the parser is listed in
`StableDeviceKey.payloadStableParsers`).

## Parser Scope

Passive-only. Routes on the `fe6b` service-data key (short and 128-bit
forms). Strict gates: exact length, version byte, v1 terminator /
v2 printable serial. Unobserved versions and lengths are left
unclaimed for future captures.

## Confidence / Attribution

Vendor attribution is **high** — 0xFE6B is a registry allocation, not a
heuristic. Field semantics (unit ID, counter) are **medium**: inferred
from 9 records / 5 devices in one scene, consistent within the capture.
Product identification is deliberately not attempted.

One caveat is recorded in the app parser: the single v2 unit also
broadcasts an ASCII-art service UUID reading `METROPOLISDEVICE` in
separate advertisements. Whether that unit is Axon fleet hardware in a
Metropolis-equipped parking garage or a third-party device squatting
Axon's UUID cannot be resolved from this capture.
