# Apple Nearby Action

## Overview

Apple Continuity type `0x0F` broadcasts indicate user-facing actions on iOS/macOS devices. These are triggered by specific user interactions like opening Wi-Fi settings, using Apple Pay, activating Siri, or setting up a new device.

Nearby Action is a strong **activity signal** — it reveals what the user is actively doing.

## BLE Advertisement Format

### Identification

- **Company ID:** `0x004C` (Apple Inc.)
- **TLV Type:** `0x0F`
- **Minimum length:** 2 bytes

Found within Apple Continuity TLV chain (see `apple-continuity.md` for TLV parsing).

### Byte Layout (within TLV value)

```
Offset  Size  Field
------  ----  -----
0       1     Action Flags
1       1     Action Type
2+      var   Action-specific data (optional)
```

### Action Types

| Code | Action | Trigger |
|------|--------|---------|
| `0x01` | Apple TV Setup | Setting up Apple TV |
| `0x04` | Hey Siri | Siri activation |
| `0x05` | Apple TV Keyboard | Text input on Apple TV |
| `0x06` | Apple TV Pair | Pairing with Apple TV |
| `0x07` | Internet Relay | Internet sharing |
| `0x08` | Setup New Phone | iPhone setup/migration |
| `0x09` | WiFi Password | Wi-Fi password sharing prompt |
| `0x0A` | HomeKit Setup | Setting up HomeKit accessory |
| `0x0B` | Handoff | App handoff between devices |
| `0x0D` | Tethering | Personal hotspot/tethering |
| `0x0E` | Apple Pay | Apple Pay transaction |
| `0x13` | Apple TV Remote | Using iPhone as Apple TV remote |

### Action Flags (byte 0)

Encodes additional context for the action. Interpretation varies by action type. Not fully documented in public research.

## Identity Hashing

```
identifier = SHA256("{mac}:{payload_hex}")[:16]
```

## Raw Packet Examples

```
# WiFi Password sharing prompt
4c 00 0f 03 40 09 00
│  │  │  │  │  │  └── action-specific data
│  │  │  │  │  └───── action_type (0x09 = WiFi Password)
│  │  │  │  └──────── action_flags
│  │  │  └─────────── length (3 bytes)
│  │  └────────────── type (0x0F = Nearby Action)
│  └───────────────── company ID high
└──────────────────── company ID low (Apple)

# Apple Pay transaction
4c 00 0f 02 00 0e
                └── action_type (0x0E = Apple Pay)
```

## Use Cases for Detection

- **WiFi Password (0x09):** Someone opened WiFi settings — useful for detecting new visitors trying to connect
- **Apple Pay (0x0E):** Active payment — strong presence signal
- **Hey Siri (0x04):** Voice assistant activation
- **Setup New Phone (0x08):** Someone is setting up a new device nearby
- **Tethering (0x0D):** Someone is sharing their cellular connection

## References

- [furiousMAC/continuity — Nearby Action](https://github.com/furiousMAC/continuity/blob/master/messages/nearby_action.md)
