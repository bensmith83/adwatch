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
| EID   | `0x40`     | Ephemeral identifier (rotating 8-byte ID, resolved server-side) |

Note: the canonical Eddystone protocol spec defines the EID frame at
`0x30`. In practice we observe EID frames at `0x40` in the wild (the
high-nibble variant is used by some vendors, including JBL audio
products). The parser accepts `0x40` to handle these captures.

## EID frame (0x40)

The **Eddystone-EID** frame carries an 8-byte ephemeral identifier
that rotates on a schedule configured at beacon registration time
(commonly every few minutes). The rotating ID is resolved to a stable
beacon identity by a registered resolver service — without resolver
access, the EID cannot be linked across rotation windows.

### Wire Format

```
[frame_type:1=0x40] | [tx_power:1] | [eid:8] | [optional trailing bytes...]
```

| Offset | Bytes | Field |
|--------|-------|-------|
| 0      | 1     | Frame type (`0x40`) |
| 1      | 1     | Ranging data / TX power (signed int8, dBm @ 0m) |
| 2–9    | 8     | Ephemeral identifier (rotating) |
| 10+    | N     | Optional vendor-specific trailing bytes (not in canonical spec) |

The canonical Eddystone-EID frame is **exactly 10 bytes**. Captures
in the wild (e.g. JBL Endurance Peak 4 earbuds) often include
**11–12 trailing bytes** of vendor-specific extras. The parser
surfaces these as `metadata["trailing_bytes_hex"]` without
interpreting them.

### Captured Example (JBL Endurance Peak 4)

```
40 c0 cd 80 98 92 bd 01 93 2b 30 45 94 28 1b 4a 24 b9 82 29 7a e1
```

Decoded:

| Field        | Value |
|--------------|-------|
| Frame type   | `0x40` (EID) |
| TX power     | -64 dBm @ 0m |
| EID          | `cd809892bd01932b` |
| Trailing     | `304594281b4a24b982297ae1` (12 bytes, vendor-specific) |

The same advertisement also exposed an empty `0x2EFC` service-data
entry alongside the FEAA frame — a JBL-specific marker. The parser
ignores siblings and matches purely on the FEAA `0x40` prefix.

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
- BT SIG 16-bit UUID `0xFEAA` → Google Inc.
