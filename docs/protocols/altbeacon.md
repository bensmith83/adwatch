# AltBeacon

## Overview

**AltBeacon** is an open beacon protocol published by Radius Networks
in 2014 as a vendor-neutral alternative to Apple iBeacon. Unlike
iBeacon, which mandates Apple's company ID `0x004C`, AltBeacon allows
any company ID — the protocol is identified by the **`0xBE 0xAC`
magic bytes** at offset 2–3 of the manufacturer-data payload.

Radius Networks' own deployments use SIG company ID `0x0118` (Radius
Networks, Inc.). Other vendors (Estimote, Kontakt.io, BlueUp, plus
custom enterprise deployments) use the AltBeacon format under their
own SIG-assigned CIDs.

## Wire Format

```
[CID:2] | BE AC | [UUID:16] | [major:2] | [minor:2] | [ref_rssi:1] | [mfg_reserved:1]
```

Total: 26 bytes manufacturer-data payload (including the 2-byte CID).

| Offset | Bytes | Field |
|--------|-------|-------|
| 0–1    | 2     | Company ID (any SIG-assigned CID) |
| 2–3    | `BE AC` | AltBeacon magic |
| 4–19   | 16    | Beacon UUID (proximity identifier) |
| 20–21  | 2     | Major (big-endian) |
| 22–23  | 2     | Minor (big-endian) |
| 24     | 1     | Reference RSSI at 1m (signed int8) |
| 25     | 1     | Manufacturer-reserved byte |

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Manufacturer data | starts with `<CID:2> BE AC` | The `BE AC` magic is the spec-defined identifier |
| Company ID | Any | Most commonly `0x0118` (Radius Networks) or `0x004C` (Apple) when riding alongside iBeacon |

The parser is **CID-agnostic** — it matches purely on the `BE AC`
magic bytes. At registry-match time the parser is associated with
CIDs `0x004C` and `0x0118` (the two most likely to advertise
AltBeacon frames); other CIDs would need adding to the registry but
parsing logic would handle them.

## Captured Example

Real capture from adwatch research export (CID `0x0118`):

```
18 01 BE AC 43 A2 BC 29 C1 11 4A 76 8B 6F 78 AE \
            CB 14 2E 5A 00 32 17 AF BD 00
```

Decoded:

| Field        | Value |
|--------------|-------|
| Company ID   | `0x0118` (Radius Networks) |
| UUID         | `43a2bc29-c111-4a76-8b6f-78aecb142e5a` |
| Major        | 50 |
| Minor        | 6063 |
| Reference RSSI | -67 dBm @ 1m |
| Mfg reserved | `0x00` |

## Identity Hashing

```
identifier_hash = SHA256("altbeacon:{uuid}:{major}:{minor}")[:16]
```

The UUID/major/minor triple is the spec-defined identity — multiple
physical beacons can share a UUID-major prefix and differ only by
minor (typical for indoor-positioning deployments where major =
floor, minor = grid cell).

## What We Cannot Parse Without GATT

The advertisement is the entire payload — AltBeacon is a pure
broadcast protocol. There are no GATT services exposed; any
"connectable" AltBeacon hardware uses a separate vendor service for
configuration (battery, firmware updates), not the AltBeacon spec
itself.

## References

- [AltBeacon GitHub specification](https://github.com/AltBeacon/spec)
- [Radius Networks AltBeacon spec PDF](https://github.com/AltBeacon/spec/blob/master/altbeacon-spec.pdf)
- BT SIG company ID `0x0118` → Radius Networks, Inc.
