# Eddystone

## Overview

**Eddystone** is Google's open BLE beacon protocol, published in 2015
as a vendor-neutral alternative to Apple iBeacon. Eddystone packets
ride on the SIG-assigned 16-bit service UUID `0xFEAA`, with the first
byte of the service data identifying the **frame type**.

The protocol defines four frame types:

| Frame | First byte | Purpose |
|-------|------------|---------|
| UID   | `0x00`     | Static beacon identity (10-byte namespace + 6-byte instance) |
| URL   | `0x10`     | Compressed URL (Physical Web) |
| TLM   | `0x20`     | Telemetry (battery, temperature, advertising count, uptime) |
| EID   | `0x30`     | Ephemeral identifier (rotating 8-byte ID, resolved server-side) |

**`0x40` and `0x41` are not Eddystone.** Earlier revisions of this doc
called `0x40` "the EID frame as seen in the wild" (JBL earbuds etc.) and
read tx_power + an 8-byte EID out of it. Those frames are Google's **Find
My Device network** (FMDN) beacon advertisement — a Fast Pair extension
that reuses `0xFEAA` with frame type `0x40` (normal) / `0x41`
(unwanted-tracking-protection mode), a 20- or 32-byte ephemeral identifier
and an optional hashed-flags byte. See
[`google-find-my-device-network.md`](google-find-my-device-network.md);
the NearSight `eddystone` parser declines `0x40`/`0x41` and `google_fmdn`
owns them (2026-09-02 sweep). The JBL Endurance Peak 4 capture that used to
be this doc's example lives there now.

## EID frame (0x30)

The **Eddystone-EID** frame carries an 8-byte ephemeral identifier
that rotates on a schedule configured at beacon registration time
(commonly every few minutes). The rotating ID is resolved to a stable
beacon identity by a registered resolver service — without resolver
access, the EID cannot be linked across rotation windows.

### Wire Format

```
[frame_type:1=0x30] | [tx_power:1] | [eid:8] | [optional trailing bytes...]
```

| Offset | Bytes | Field |
|--------|-------|-------|
| 0      | 1     | Frame type (`0x30`) |
| 1      | 1     | Ranging data / TX power (signed int8, dBm @ 0m) |
| 2–9    | 8     | Ephemeral identifier (rotating) |
| 10+    | N     | Optional trailing bytes (not in canonical spec) |

The canonical Eddystone-EID frame is **exactly 10 bytes**. The parser
surfaces anything past that as `metadata["trailing_bytes_hex"]` without
interpreting it. No canonical `0x30` EID frame has appeared in the
NearSight telemetry corpus so far — every `0xFEAA` frame with the high
nibble `4` was an FMDN frame — so the decode is spec-derived rather than
capture-derived.

### Identity Hashing

```
stable_key      = "eddystone_eid:{eid_hex}"
identifier_hash = SHA256(stable_key)[:16]
```

**Caveat — ephemeral by design:** because the 8-byte EID rotates
periodically, the `eddystone_eid:<eid>` stable key is only stable
within a single rotation window. It is suitable for short-window
tracking (a single scan session) but cannot link the same physical
beacon across rotations without a resolver service.

## What We Cannot Parse Without GATT

The advertisement is the entire broadcast payload. To resolve an EID
to a stable identity, a paired resolver service must be queried with
the rotating ID and a shared secret installed at beacon provisioning
time — not available from passive scanning.

## References

- [Eddystone Protocol Specification](https://github.com/google/eddystone/blob/master/protocol-specification.md)
- [Eddystone-EID frame](https://github.com/google/eddystone/blob/master/eddystone-eid/README.md)
- [`google-find-my-device-network.md`](google-find-my-device-network.md) — the `0x40`/`0x41` frames on the same UUID
- BT SIG 16-bit UUID `0xFEAA` → Google Inc.
