# Otodata Tank Monitor Protocol

## Overview

**Otodata Wireless Network Inc.** (Montréal, QC) builds cellular + BLE
remote tank-level monitors for propane and heating-oil tanks, sold under
the **Nee-Vo** brand and white-labelled by propane distributors
(Ferrellgas, AmeriGas and regional dealers). The monitors sit on the tank
gauge, report level over cellular to the Nee-Vo cloud, and *also*
broadcast a short-range BLE advertisement used by the installer app.

That BLE broadcast is passive and unencrypted, so a scanner in range of a
residential propane tank will see it.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x03B1` | SIG-assigned to *Otodata Wireless Network Inc.* — unique and uncollidable |
| Payload magic | ASCII `OTO` at manufacturer-data offset 2 | Second, independent vendor signal |
| Frame tag | 4 ASCII bytes at offset 5 | Observed: `STAT`, `TELE`, `3281` |
| Address type | random | The BLE address rotates; the frame carries no plaintext serial |
| Device class | `sensor` | |

The **CID + `OTO` magic** pair is what makes this attribution confident:
either signal alone would be circumstantial, but a payload that spells the
vendor's own name behind that vendor's own SIG slot is not a collision.

## Ad Format

All frames share a 9-byte header:

```
offset  0  1 | 2  3  4 | 5  6  7  8 | 9 ...
        b1 03 | 4f 54 4f | <4-byte ASCII tag> | frame body
        CID     "OTO"      "STAT"/"TELE"/"3281"
```

A single unit rotates through all three tags — the same physical monitor
was observed emitting `OTOSTAT`, `OTOTELE` and `OTO3281` inside one
4-minute window. This mirrors the rotating **local-name** advertisement
that older Otodata units use (`"TM6030 2034xxxx"` → `"level: 68.2 % horiz"`
→ `"unit sleeping"` → `"trbl:ACC (45.2)"`, documented by the Home
Assistant community); the manufacturer-data form is the same idea moved
into the AD `0xFF` field.

### `OTOSTAT` — 26 bytes

```
 0  1 | 2  3  4 | 5  6  7  8 | 9 | 10 11 | 12 13 | 14 15 16 17 | 18 | 19 20 | 21 22 23 24 25
b1 03 | 4f 54 4f | 53 54 41 54 | 01 | vv vv | vv vv | cc cc cc cc | 08 | dd dd | tail
```

| Bytes | Meaning | Evidence |
|-------|---------|----------|
| 9 | frame version, always `0x01` | 17/17 records |
| 10–11 | 16-bit LE value | varies per sighting: `0x0131`, `0x03fa`–`0x040d`, `0x0f5a` |
| 12–13 | **exact duplicate of bytes 10–11** | 17/17 records — a redundancy/integrity copy |
| 14–17 | 32-bit LE constant | `0x00049E80` (302 208) on two units, `0x0004BC8A` (310 922) on a third — *shared across units*, so a firmware/config constant, **not** a serial |
| 18 | always `0x08` | 17/17 records |
| 19–20 | 16-bit LE, constant per unit | `0x00B8`, `0x00B5`, `0x00AD` (184 / 181 / 173) |
| 21–25 | `05 01 00 00 00` / `05 00 00 00 00` / `01 00 00 00 00` | low-cardinality status/flags |

The duplicated 16-bit field (10–11 == 12–13) is the strongest decoded
structure in the frame. Its unit is **not** established: the observed
values (1018–1037 on one unit, 305 on another, 3930 on a third) are
consistent with a raw ADC reading or a millivolt battery reading, but the
corpus contains no ground truth to pin either, so the parser surfaces the
number without a unit.

### `OTOTELE` — 26 bytes

```
b1 03 | 4f 54 4f | 54 45 4c 45 | 02 00 | aa aa | 00 00 | bb bb bb bb | 00 00 ff 00 00 00 00
```

Bytes 15–18 read as a 32-bit LE value that is nearly identical across two
different units observed minutes apart (`0x1806733A` vs `0x18067539`, a
difference of 511) — consistent with a shared clock/epoch counter rather
than a per-device identity.

### `OTO3281` — 18 or 25 bytes

```
b1 03 | 4f 54 4f | 33 32 38 31 | <3 per-unit bytes> | 01 | ...
```

`3281` sits in the frame-tag slot but is ASCII digits, so it is likely a
model designator rather than a message type. The three bytes after the tag
differ per unit (`32 15 ad`, `d8 71 ae`, `e6 73 35`) and are the only
per-unit-distinguishing bytes in the whole family; they are surfaced as an
opaque `unit_bytes_hex`, not claimed as a serial.

## What We Cannot Parse

- Tank level percentage (the older name-based advertisement carries
  `level: NN.N %` in plaintext, but the manufacturer-data frames observed
  here do not obviously encode it)
- Tank orientation (`horiz`/`vert`)
- Trouble/fault codes
- Model or serial number as text
- Battery percentage as a calibrated value

## Identity Hashing

The BLE address is random and rotates, and no frame carries a proven
plaintext serial, so identity anchors on the outer BLE address:

```
identifier = SHA256("otodata:{mac}")[:16]
```

## Detection Significance

A sighting means a **bulk propane or heating-oil tank with a monitored
gauge** is within BLE range — normally a detached home, RV park, farm, or
commercial LPG installation. It is a reasonable proxy for "off-mains
heating/cooking fuel at this address."

## Confidence / Attribution

**High.** Two independent vendor signals (SIG CID `0x03B1` uniquely
assigned to Otodata, plus the literal ASCII string `OTO` in the payload),
29 records across 4 distinct units, and a stable internal grammar
(fixed header, three frame tags, invariant constants) that holds on every
record in the cluster. What is *not* claimed: the physical meaning of any
numeric field, and the specific hardware model.

## References

- Bluetooth SIG `company_identifiers.yaml` — `0x03B1 = Otodata Wireless
  Network Inc.`
- [Home Assistant community: "Bluetooth propane tank monitor: ESPhome,
  Otodata, Nee-vo, Ferrellgas,
  BLE"](https://community.home-assistant.io/t/bluetooth-propane-tank-monitor-esphome-otodata-nee-vo-ferrellgas-ble/430476)
  — documents the sibling rotating-local-name advertisement on Otodata
  TM-series hardware.
