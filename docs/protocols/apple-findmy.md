# Apple Find My (Offline Finding)

## Overview

Apple Continuity type `0x12` is broadcast by AirTags and Find My network accessories. The payload contains a fragment of a rotating EC (Elliptic Curve) public key used by Apple's crowd-sourced location tracking system.

## BLE Advertisement Format

### Identification

- **Company ID:** `0x004C` (Apple Inc.)
- **TLV Type:** `0x12`
- **Typical length:** 28+ bytes (EC key fragment)
- **Minimum length for parsing:** 2 bytes

Found within Apple Continuity TLV chain (see `apple-continuity.md` for TLV parsing).

### What We Know

The payload contains an EC P-224 public key fragment that rotates periodically. Apple's Offline Finding protocol uses these keys so that:

1. The AirTag/accessory broadcasts a rotating public key
2. Nearby Apple devices encrypt their location with this public key
3. Only the owner (who has the corresponding private key) can decrypt the location reports

### What We Don't Parse

The internal structure of the EC key fragment is not decoded — we treat the entire payload as an opaque rotating identifier. Full parsing would require understanding Apple's key derivation schedule and the Offline Finding cryptographic protocol.

## Identity Hashing

```
identifier = SHA256("{mac}:{payload_hex}")[:16]
```

Both the MAC and the EC key fragment rotate, so this identifier is **short-lived** (~15 minutes).

## Detection Significance

- Indicates an AirTag or Find My accessory is nearby
- High volume of Find My advertisements in any public space
- Cannot determine the owner from the advertisement alone
- Useful for tracker detection and counting

## References

- Heinrich et al., "Who Can Find My Devices? Security and Privacy of Apple's Crowd-Sourced Bluetooth Location Tracking System", PETS 2021
- [OpenHaystack](https://github.com/seemoo-lab/openhaystack) — Open-source Apple Find My research project
- [Apple Find My Network Accessory Specification](https://developer.apple.com/find-my/) (requires MFi enrollment)
