# CID 0x41A4 mystery tracker

## Overview

An unidentified BLE tracker family that broadcasts 29- and 67-byte extended-advertising manufacturer-data frames under a vanity company ID `0x41A4`. The CID is **not assigned** by the Bluetooth SIG (the registry tops out near `0x10C7`), so this is the same vanity-CID pattern documented by `VictronEnergyParser` (`"VE"`) and `FHPSmartFanParser` (`"WF"`). The vendor is unconfirmed; we surface a presence-level identification anchored on two byte regions that are stable across every capture we have.

## BLE Advertisement Format

### Identification anchors

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x41A4` | LE `a4 41` — not in the SIG `company_identifiers.yaml` registry |
| Family constant A | `1b 96 04 36` at bytes [9..12] | Identical across every captured frame |
| Family constant B | `b0 00 00 e2 a2 6b 00 00 59 96 dd fe` at bytes [16..27] | Identical across every captured frame |

Both constants must match — neither alone is unique enough to anchor a vanity CID.

### Frame variants

**Short (29 bytes total)**

```
a4 41 | XX XX XX XX XX XX XX | 1b 96 04 36 | XX | dc 0b | b0 00 00 e2 a2 6b 00 00 59 96 dd fe | XX
└──┬─┘ └──────┬────────────┘ └────┬──────┘ └┬┘ └──┬──┘ └─────────────────┬──────────────────┘ └┬┘
 CID    rolling counter region  const A   var const   family constant B                       var
```

**Long (67 bytes total)** — same prefix as short, plus a trailing embedded TLV starting at byte 28:

```
... | 11 02 11 02 <4-byte token> 25 00 01 <state> 00 78 6d eb f2 56 <byte> 06 07 08 09 0a 0b 0c 0d 0e 0f
     └────┬────┘ └─────┬───────┘ ┬┬ ┬┬ ┬┬ └─┬───┘ ┬┬ └─────┬──────┘ └─┬──┘ └──────────┬──────────────────┘
     nested CID    rotating tok  type ?  ?  state ?    fingerprint   tag  SDK default-fill tail
```

The `11 02` doubling at the head of the TLV mirrors the Telink BLE SDK frame-builder habit also seen in `HonorBLEParser`. The trailing `06 07 08 09 0a 0b 0c 0d 0e 0f` is the canonical SDK default-fill pattern (Nordic / Espressif / Telink reference firmware emit this when the host application forgets to populate the optional payload region).

The 4-byte `embedded_token` alternates between two stable values (e.g. `6d51f2eb` and `df51f2eb`) across consecutive ads from the same device, with the matching `embedded_state` byte (`0x8b` vs `0x99`) tracking alongside. Likely two beacons or two pairing-state pings sharing a unit.

### What we can extract

| Field | Notes |
|-------|-------|
| `family_constant_a`, `family_constant_b` | Lock anchors, surfaced for verification |
| `frame_size` | `short` / `long` / `long_unfamiliar` |
| `embedded_token_hex` | Long-frame only; rotating per-device token |
| `embedded_state_hex` | Long-frame only; observed values `0x8b`, `0x99` |
| `embedded_type_byte` | Always `0x25` in captures so far |
| `embedded_fingerprint_hex` | Stable `78 6d eb f2 56` per device generation |
| `embedded_tail_present` | `true` when the `06 07 08 ... 0f` SDK leftover is intact |

### What we cannot extract

- Vendor / SKU (vanity CID + no public reverse-engineering)
- Stable per-device serial (the captured tokens rotate)
- Battery / state semantics beyond the surfaced bytes

## Detection significance

- Identifies a recurring extended-ADV tracker we don't otherwise classify (36 records across 4 export sessions).
- Vanity CID + Telink-style frame layout + SDK default-fill all point to low-budget OEM firmware shipping on a Telink chipset — useful context when assessing how trustworthy or stable the device is.
- Both byte anchors must match, so the parser will not over-fire on unrelated 0x41A4 broadcasts if someone else ever uses the same vanity slot.

## References

- Bluetooth SIG `company_identifiers.yaml` (verifies that 0x41A4 is unassigned).
- Captures: `research/adwatch_export 8/9/10/12.json`.
- Telink BLE SDK reference firmware (cross-reference for the `06 07 ... 0f` default-fill tail).
