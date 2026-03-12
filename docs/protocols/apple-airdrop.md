# Apple AirDrop

## Overview

AirDrop broadcasts (Apple Continuity type `0x05`) are emitted when an iOS or macOS device is actively sharing or receiving files, or has AirDrop set to "Everyone" or "Contacts Only". These advertisements contain truncated hashes of the user's contact information (AppleID, phone number, email addresses).

AirDrop presence is a **strong activity signal** — it indicates active device usage, not just passive presence.

## BLE Advertisement Format

### Identification

- **Company ID:** `0x004C` (Apple Inc.)
- **TLV Type:** `0x05`
- **Minimum length:** 8 bytes

Found within Apple Continuity TLV chain (see `apple-continuity.md` for TLV parsing).

### Byte Layout (within TLV value)

```
Offset  Size  Field
------  ----  -----
0–1     2     AppleID hash (truncated SHA256)
2–3     2     Phone number hash
4–5     2     Email hash
6–7     2     Email2 hash
8+      var   Additional data (optional)
```

All hashes are truncated to 2 bytes (16 bits) from the full SHA256 of the contact identifier.

### Identity Hashes

The 2-byte hashes are derived from:
- **AppleID hash:** SHA256 of the user's AppleID email
- **Phone hash:** SHA256 of the user's phone number
- **Email hash:** SHA256 of primary email
- **Email2 hash:** SHA256 of secondary email (if configured)

With only 2 bytes per hash, there are collisions — these are not unique identifiers for a specific person. They're useful for:
- Grouping advertisements from the same device session
- Detecting that *someone* is AirDropping (activity signal)
- Correlating with known contact hashes (if you have the source values)

### Zero Hashes

A hash of `0000` typically means that contact method is not configured or not being shared in the current AirDrop mode.

## Identity Hashing (adwatch)

```
combined = "{appleid_hash}{phone_hash}{email_hash}{email2_hash}"
identifier = SHA256(combined)[:16]
```

Note: This is based on the contact hashes, NOT the MAC. This means the same person's AirDrop identity is somewhat stable even across MAC rotations (the contact hashes don't change).

## Raw Packet Examples

```
# AirDrop advertisement within Apple Continuity TLV
4c 00 05 08 a1 b2 c3 d4 e5 f6 00 00
│  │  │  │  │     │     │     └───── email2_hash (0x0000 = not set)
│  │  │  │  │     │     └────────── email_hash
│  │  │  │  │     └──────────────── phone_hash
│  │  │  │  └────────────────────── appleid_hash
│  │  │  └───────────────────────── length (8 bytes)
│  │  └──────────────────────────── type (0x05 = AirDrop)
│  └─────────────────────────────── company ID high
└────────────────────────────────── company ID low (Apple)
```

## Privacy Notes

- Contact hashes are intentionally truncated to 2 bytes to limit identification
- Researchers have demonstrated rainbow table attacks against phone number hashes (limited phone number space makes brute-force feasible)
- AirDrop set to "Contacts Only" still broadcasts hashes — resolution happens server-side
- "Receiving Off" prevents AirDrop advertisements entirely

## References

- [furiousMAC/continuity — AirDrop](https://github.com/furiousMAC/continuity/blob/master/messages/airdrop.md)
- Stute et al., "A Billion Open Interfaces for Eve and Mallory: MitM, DoS, and Tracking Attacks on iOS and macOS Through Apple Wireless Direct Link", USENIX Security 2019
- Heinrich et al., "Who Can Find My Devices? Security and Privacy of Apple's Crowd-Sourced Bluetooth Location Tracking System", PETS 2021
