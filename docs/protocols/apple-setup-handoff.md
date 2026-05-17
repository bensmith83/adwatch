# Apple Setup Handoff — Quick Start / iPhone Migration

## Overview

Apple's **Setup Handoff** (sometimes called *Quick Start* or *Setup Assistant Handoff*) is the proximity-pairing protocol used when:

- An iPhone is being **migrated to a new iPhone** (Setup Assistant → "Set Up with iPhone")
- A new Apple Watch is being paired
- A new HomePod, Apple TV, or AirPods is being set up via Proximity Setup

Unlike most Apple Continuity messages, Setup Handoff is **not** carried in manufacturer-specific data with company ID `0x004C`. It is carried as **service data on the 16-bit service UUID `0xFD44`** with an Apple-specific 4-byte header that echoes the company ID.

This makes it invisible to parsers that only walk the standard Continuity TLV chain on manufacturer data — those will see a frame with no `0x004C` payload at all.

## Real-world capture

Observed continuously (~5 Hz) from an iPhone running Setup Assistant during an iPhone-to-iPhone migration:

```
serviceData["FD44"] = 4c 00 00 00 18 20 00 00 95 00 00 00 00 00 00 00 00 00 00 00 00
```

Same MAC + same payload for the entire transfer window.

## BLE Advertisement Format

### Identification

- **AD Type:** `0x16` (Service Data — 16-bit UUID)
- **Service UUID:** `0xFD44` (Apple Inc.)
- **Payload prefix:** `4C 00 00 00` (Apple company ID echo + 2-byte header)
- **Followed by:** subtype byte, a flags byte, then opaque payload

```
┌──────────────────────────────────────────────────────┐
│ Apple Header (4 bytes)                               │
│   4C 00     Apple company ID echo (little-endian)    │
│   00 00     Reserved / zero in observed samples      │
├──────────────────────────────────────────────────────┤
│ Body                                                 │
│   1 byte    Subtype (e.g. 0x18 = Setup Handoff)      │
│   1 byte    Flags / protocol byte (NOT a length —    │
│             Apple commonly reuses what would be a    │
│             TLV-length slot for protocol-specific    │
│             data)                                    │
│   N bytes   Opaque session / auth payload            │
└──────────────────────────────────────────────────────┘
```

### Why the second byte is not a length

Some Apple Continuity TLVs in the manufacturer-data form follow a strict `(type, length, value)` grammar, but in the FD44 service-data form Apple repurposes that slot for protocol flags. In the observed capture the byte reads `0x20` while only 15 bytes of opaque payload follow — interpreting it as a length yields a value (32) that is impossible to fit in the BLE advertisement budget. Parsers should treat it as a flags / sub-protocol byte and consume everything after it as the body.

## Subtype 0x18 — Setup Handoff (Quick Start)

Emitted by an iPhone in Setup Assistant while it advertises itself to a nearby device for Quick Start (new-iPhone migration, new Apple Watch pairing, etc.).

### Byte layout

```
Offset  Size  Field
------  ----  -----
4       1    Subtype = 0x18 (Setup Handoff)
5       1    Flags byte (observed `0x20` in iPhone migration captures)
6       1    Inner flags / reserved (observed `0x00`)
7       1    Reserved (observed `0x00`)
8       1    Setup-state indicator (observed `0x95`)
9+      var  Opaque session / auth payload (zero-padded in captures)
```

The byte-8 value of `0x95` was constant across 328 captured frames from the same migrating iPhone, suggesting it is a fixed marker rather than a counter. The trailing bytes are opaque (likely a session token or auth tag derived from the device's Apple ID / iCloud account).

### Behavior

| Property | Value |
|----------|-------|
| Rate | ~5 Hz while Setup Assistant is on screen |
| Duration | Throughout the Quick Start handshake window |
| MAC rotation | RPA rotates every ~15 min; payload stays constant |
| AddressType | random (RPA) |
| Local name | Not advertised |
| Other service UUIDs | Sometimes accompanied by a 128-bit custom UUID (varies per session) |

## Other subtypes

The same TLV grammar accommodates additional subtypes (e.g. variants emitted during HomePod / Apple Watch / Apple TV setup). They are not yet fully documented; the parser reports them as `Unknown (0xNN)` with the raw value bytes exposed in `payload_hex` for forensic review.

## Identity Hashing (adwatch)

```
identifier = SHA256("{mac}:{tlv_value_hex}")[:16]
```

The TLV value is mostly opaque, but for a given Setup-Handoff session it is stable. Combined with the MAC, this produces a per-session identifier that:

- Distinguishes between two iPhones being set up simultaneously
- Does NOT bridge MAC rotations (the MAC changes ~every 15 min; the payload doesn't change, but the hash does because it includes MAC)

## Raw Packet Example

```
# iPhone Quick Start handoff (real capture)
serviceData[FD44] = 4c 00 00 00 18 20 00 00 95 00 00 00 00 00 00 00 00 00 00 00 00
                    └────┬────┘ │  │  └──────────────────┬──────────────────────┘
                         │      │  │                     └── 15-byte opaque body
                         │      │  └── Flags / protocol byte (NOT a length)
                         │      └── Subtype 0x18 (Setup Handoff / Quick Start)
                         └── Apple header (company ID echo + reserved)
```

## Detection Notes

- A device emitting FD44 + subtype `0x18` is **actively in Setup Assistant**. This is a rare, high-signal event — useful for surfacing "someone nearby is setting up a new iPhone" in a UI.
- The same iPhone may simultaneously emit standard Continuity `NearbyInfo` (manufacturer data) — both parsers will fire on the same advertisement record.
- Setup Handoff is NOT emitted by Find My broadcasts, NOT by Handoff (clipboard sync), and NOT by ordinary AirPlay/AirDrop. It is specific to first-time-setup flows.

## References

- [furiousMAC/continuity](https://github.com/furiousMAC/continuity) — Apple Continuity Wireshark dissector (catalog of TLV subtypes)
- Stute et al., "Disrupting Continuity of Apple's Wireless Ecosystem Security", USENIX Security 2021
- Apple Developer Documentation — Setting Up Quick Start (user-facing description of the proximity-pairing flow)
