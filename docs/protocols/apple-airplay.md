# Apple AirPlay Target

## Overview

Apple Continuity type `0x09` is broadcast by devices acting as AirPlay targets — Apple TVs, HomePods, AirPlay-enabled speakers and TVs. These advertisements contain flags, a configuration seed, and optionally an IPv4 address.

AirPlay Target ads identify media infrastructure rather than personal devices.

## BLE Advertisement Format

### Identification

- **Company ID:** `0x004C` (Apple Inc.)
- **TLV Type:** `0x09`
- **Minimum length:** 3 bytes

Found within Apple Continuity TLV chain (see `apple-continuity.md` for TLV parsing).

### Byte Layout (within TLV value)

```
Offset  Size  Field
------  ----  -----
0       1     Flags
1–2     2     Config Seed (big-endian: byte[1] << 8 | byte[2])
3–5     3     Padding (optional)
6–9     4     IPv4 Address (optional, when length ≥ 10)
```

### Flags (byte 0)

Encodes AirPlay capabilities and state. Not fully documented in public research.

### Config Seed (bytes 1–2)

16-bit value assembled big-endian. Changes when the AirPlay target's configuration changes (e.g., name change, pairing reset). Can be used to detect configuration changes over time.

### IPv4 Address (bytes 6–9, optional)

When present (payload length ≥ 10), contains the device's IPv4 address:

```
ipv4 = f"{byte[6]}.{byte[7]}.{byte[8]}.{byte[9]}"
```

## Identity Hashing

```
identifier = SHA256("{mac}:{payload_hex}")[:16]
```

## Raw Packet Examples

```
# AirPlay target with config seed 0x1234, no IPv4
4c 00 09 03 80 12 34
│  │  │  │  │  └──── config_seed (0x1234)
│  │  │  │  └─────── flags (0x80)
│  │  │  └────────── length (3 bytes)
│  │  └───────────── type (0x09 = AirPlay Target)
│  └──────────────── company ID high
└─────────────────── company ID low (Apple)

# AirPlay target with IPv4 address 192.168.1.50
4c 00 09 0a 80 12 34 00 00 00 c0 a8 01 32
                                │  │  │  └── 50
                                │  │  └───── 1
                                │  └──────── 168
                                └─────────── 192
```

## Typical Devices

- Apple TV (all generations)
- HomePod / HomePod mini
- AirPlay 2 enabled TVs (Samsung, LG, Sony, Vizio)
- AirPlay 2 enabled speakers (Sonos, Bose, etc.)
- Mac computers acting as AirPlay receivers (macOS Monterey+)

## References

- [furiousMAC/continuity](https://github.com/furiousMAC/continuity)
