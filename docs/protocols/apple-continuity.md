# Apple Continuity — Nearby Info & Handoff

## Overview

Apple devices continuously broadcast BLE advertisements using manufacturer-specific data with Company ID `0x004C`. These use a Type-Length-Value (TLV) structure containing multiple message types. The two most important for device detection are **Nearby Info** (type `0x10`) and **Handoff** (type `0x0C`).

Nearby Info is the primary signal for iOS/macOS device counting — it broadcasts continuously on iOS 12+ devices.

## BLE Advertisement Format

### Identification

- **AD Type:** `0xFF` (Manufacturer Specific Data)
- **Company ID:** `0x004C` (Apple Inc., little-endian: `4c 00`)
- **Structure:** TLV (Type-Length-Value) after company ID

```
┌──────────────────────────────────────────────────────┐
│ Company ID: 0x4C 0x00 (Apple Inc., little-endian)    │
├──────────────────────────────────────────────────────┤
│ TLV Message 1                                        │
│   ├── Type (1 byte)                                  │
│   ├── Length (1 byte)                                │
│   └── Value (variable)                               │
├──────────────────────────────────────────────────────┤
│ TLV Message 2 (optional)                             │
│   └── ...                                            │
└──────────────────────────────────────────────────────┘
```

Multiple TLV messages can appear in a single advertisement. Walk the chain by reading type, length, advancing by `2 + length` bytes.

### TLV Parsing

```
offset = 2  (skip company ID)
while offset < len(data) - 1:
    msg_type = data[offset]
    msg_len  = data[offset + 1]
    payload  = data[offset + 2 : offset + 2 + msg_len]
    offset  += 2 + msg_len
```

## Nearby Info (Type 0x10)

The most useful message for phone counting. Broadcasts continuously on modern iOS devices.

### Byte Layout

```
Offset  Size  Field
------  ----  -----
0       1     Status Flags (high nibble) + Action Code (low nibble)
1       1     Data Flags
2–4     3     Authentication Tag (rotating identifier)
```

Typical length: 5 bytes.

### Status Flags (high nibble of byte 0)

| Bit | Meaning |
|-----|---------|
| 0x01 | Primary iCloud account device |
| 0x02 | Unknown |
| 0x04 | AirDrop Receiving enabled |
| 0x08 | Unknown |

### Action Code (low nibble of byte 0)

| Code | Activity | Notes |
|------|----------|-------|
| `0x00` | Unknown | |
| `0x01` | Reporting disabled | |
| `0x03` | Idle | Screen locked |
| `0x05` | Audio (locked) | Music playing, screen off |
| `0x07` | Active | Screen on |
| `0x09` | Video | Screen on, video playing |
| `0x0A` | Watch unlocked | Apple Watch on wrist |
| `0x0B` | Recent interaction | |
| `0x0D` | Driving | |
| `0x0E` | Phone call | |

Action code `0x0A` indicates an Apple Watch rather than a phone.

### Data Flags (byte 1)

| Bit | Meaning |
|-----|---------|
| 0x04 | WiFi on/off indicator |
| 0x10 | Authentication Tag present |
| 0x20 | Apple Watch locked |
| 0x40 | Auto Unlock on Watch enabled |
| 0x80 | Auto Unlock enabled |

Common combinations:
- `0x98` — Unlocked Apple Watch
- `0x18` — Locked watch / WiFi off

### Authentication Tag (bytes 2–4)

3-byte rotating value. May persist across MAC address rotations for short periods, enabling cross-rotation tracking.

### Identity Hashing

```
identifier = SHA256("{mac}:{auth_tag_hex}")[:16]
```

The MAC rotates every ~15 minutes (Resolvable Private Address). The auth tag may persist slightly longer, providing a bridge across rotations.

## Handoff (Type 0x0C)

Sent when using Continuity features (Safari, Notes, Mail, etc.). Contains encrypted payload with a sequence number.

### Byte Layout

```
Offset  Size  Field
------  ----  -----
0–7     8     Encrypted payload (IV + data)
8+      var   Remainder (optional)
```

Minimum length: 8 bytes.

### Key Property

Sequence numbers are monotonically increasing and **persist across MAC rotations**. This is a known tracking vulnerability documented in academic research.

### Identity Hashing

```
identifier = SHA256("{mac}:{first_8_bytes_hex}")[:16]
```

## Rotation Behavior

| Component | Rotation Interval | Notes |
|-----------|------------------|-------|
| BLE MAC Address | ~15 minutes | Resolvable Private Address (RPA) |
| Nearby Info Auth Tag | Varies | May persist across MAC rotations |
| Nearby Info Data Fields | Seconds–minutes | Can persist across MAC rotations |
| Handoff Sequence Number | Never resets | Persists across MAC rotations |

**Critical finding:** Nearby Info data fields do NOT immediately change when MAC rotates, enabling cross-rotation tracking for short periods.

## Device Type Detection

| Device | Nearby Info Behavior |
|--------|---------------------|
| iPhone (iOS 12+) | Continuous broadcast, 5-byte Nearby Info |
| iPad | Continuous broadcast, same format |
| MacBook | Variable, may include public MAC during Handoff |
| Apple Watch | Action code `0x0A` when on wrist and unlocked |
| iOS < 12 | May time out after inactivity |

## Raw Packet Examples

```
# iPhone, active (screen on), Nearby Info
4c 00 10 05 37 18 a1 b2 c3
│  │  │  │  │  │  └──────── auth_tag (3 bytes)
│  │  │  │  │  └─────────── data_flags (0x18)
│  │  │  │  └──────────────  status_flags=0x3, action_code=0x7 (active)
│  │  │  └───────────────── length (5 bytes)
│  │  └──────────────────── type (0x10 = Nearby Info)
│  └─────────────────────── company ID high byte
└────────────────────────── company ID low byte (Apple)

# Apple Watch, unlocked on wrist
4c 00 10 05 1a 98 d4 e5 f6
                │  │
                │  └── data_flags=0x98 (unlocked watch)
                └───── status_flags=0x1, action_code=0xA (watch_unlocked)
```

## References

- Martin et al., "Handoff All Your Privacy — A Review of Apple's Bluetooth Low Energy Continuity Protocol", PETS 2019
- Celosia & Cunche, "Discontinued Privacy: Personal Data Leaks in Apple Bluetooth-Low-Energy Continuity Protocols", PETS 2020
- Stute et al., "Disrupting Continuity of Apple's Wireless Ecosystem Security", USENIX Security 2021
- [furiousMAC/continuity](https://github.com/furiousMAC/continuity) — Apple Continuity Wireshark dissector
