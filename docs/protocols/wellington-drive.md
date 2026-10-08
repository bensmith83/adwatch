# Wellington Drive commercial-refrigeration beacon (CID 0x0578)

## Overview

**Wellington Drive Technologies Ltd** (Auckland, NZ) holds Bluetooth SIG
company identifier `0x0578`. Wellington makes electronically commutated
(ECM) fan motors and connected controllers for **commercial beverage
coolers and refrigerated merchandisers** — the branded glass-door coolers
in convenience stores, supermarkets and fuel stations — and sells a
"Connect" IoT layer on top of them (cooler health, door/traffic
telemetry, asset tracking) that talks to a phone app over BLE.

Two units have been captured so far, on consecutive sweep days, both
from fixed random addresses that did not rotate inside the capture:

| Date | Serial | Records · sightings | Frames |
|------|--------|---------------------|--------|
| 2026-08-23 | `MF########` | 4 · 6 | serial frames only (deferred at n=1) |
| 2026-08-24 | `C#########` | 36 · 56 | serial frames |
| 2026-08-24 | (second radio, no serial) | 2 · 21 | status frames |

The 08-24 serial and status frames came from two different CoreBluetooth
identifiers in the same 15-minute window, so they are most likely two
radios (or two units) in one installation.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0578` (LE wire `78 05`) | SIG-assigned to *Wellington Drive Technologies Ltd* |
| Frame type | byte 2: `0x01` serial, `0x03` status | Structural gate |
| Serial | 16-byte NUL-padded ASCII at [6..22) of the serial frame | Per-unit; observed 10 characters on both units |
| Service UUIDs | `0x1800` advertised **twice** | GAP service UUID listed twice on every serial frame of both units — a firmware quirk, useful corroboration, not gated on |
| Address type | random (static within a capture) | |
| Device class | `hvac_controller` | Refrigeration controller / ECM motor controller |

## Ad Format

### Serial frame — 22 bytes

```
offset  0  1 | 2  | 3  | 4  5  | 6 … 21
        78 05 | 01 | 00 | vv vv | 43 xx xx xx xx xx xx xx xx xx 00 00 00 00 00 00
        CID     type rsv  int16   "C#########" + NUL padding to 16 bytes
                          LE
```

| Bytes | Meaning | Evidence |
|-------|---------|----------|
| 2 | frame type `0x01` | 40/40 serial frames across both units |
| 3 | reserved / flags, always `0x00` | 40/40 |
| 4–5 | signed 16-bit little-endian value | see below |
| 6–21 | 16-byte serial field, ASCII, NUL-padded | `C#########` + 6 × `00`; `MF########` + 6 × `00` |

**The 16-bit value.** On the 08-24 unit it traced a clean **triangle
wave** inside the 15-minute capture: −20 → 500 in steps of 10 at roughly
1.7 units/s, then back down at the same rate, period ≈ 10 min (observed
values: −20, −10, 0, 10, 50, 60, …, 460, 480, 500). The 08-23 unit read
380, 530 and 540. Every observed value is a multiple of 10. Its physical
meaning is **not** claimed: a tenths-scaled measurement swinging
symmetrically between −2.0 and 50.0 (or 54.0) is consistent with a
demo/test ramp, a sweep-mode setpoint, or a counter — nothing in the
frame says which. The parser surfaces it as `value_int16_le` plus the raw
`value_hex`.

### Status frame — 7 bytes

```
offset  0  1 | 2  | 3  4  5  6
        78 05 | 03 | 2c c1 00 00
        CID     type 4-byte body (raw)
```

Two payloads seen (`2c c1 00 00` × 19 sightings, `2d 41 00 00` × 2), five
minutes apart on one radio. Byte 3 stepped `0x2c → 0x2d` and byte 4
flipped its high bit (`0xc1 → 0x41`); with n=2 neither is decoded. The
body is reported raw as `body_hex`.

### Parser gate

- company ID `0x0578`, **and**
- either (type `0x01`, total length 22, serial field = ≥1 printable ASCII
  byte followed only by NUL padding) **or** (type `0x03`, total length 7).

Any other `0x0578` shape is left unclaimed.

## Identity Hashing

Serial frames key identity on the serial, which survives address
rotation:

```
identifier = SHA256("wellington_drive:{serial}")[:16]
stableKey  = "wellington_drive:{serial}"
```

Status frames carry no per-unit field, so they fall back to the BLE
address and publish no `stableKey`:

```
identifier = SHA256("wellington_drive:mac:{address}")[:16]
```

`serial` is tagged `uniqueStable` (kept off the telemetry wire).

## What We Cannot Parse

- The physical unit of the 16-bit value (temperature? setpoint? counter?)
- Cooler state: door, compressor, fan speed, alarms
- Product model (ECM motor vs controller vs beacon module)
- Whether the status frame's two radios are one cooler or two

## Detection Significance

A sighting means **a connected commercial cooler or refrigerated
merchandiser is within BLE range** — a store, fuel station, vending
alcove or back-of-house cold room. Two of the three 08-24 clusters in the
same 18-minute window (this one and a Texas Instruments rotating sensor
beacon) fit a retail scene.

## Confidence / Attribution

**Vendor: high.** A real SIG company-ID allocation, a per-unit serial in
the payload with a consistent grammar over two units on two days, and a
distinctive firmware quirk (duplicated `0x1800`) shared by both units.

**Product family: medium.** "Commercial refrigeration ECM motor /
cooler controller" is inferred from the vendor's catalogue; the frame
carries no product code.

**Field semantics: low.** The 16-bit value and the status body are
reported raw with the observations above; no unit or state decode is
claimed.

## References

- Bluetooth SIG `company_identifiers.yaml` — `0x0578 = Wellington Drive
  Technologies Ltd`.
- NearSight `research/sweep-2026-08-23-candidates.md` (first unit,
  deferred) and `research/sweep-2026-08-24-candidates.md` (second unit,
  status frames, triangle-wave observation).
