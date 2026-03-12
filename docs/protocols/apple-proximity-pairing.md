# Apple Proximity Pairing (AirPods & Beats)

## Overview

Apple Continuity type `0x07` is used by AirPods and Beats accessories to broadcast their status to nearby Apple devices. These advertisements contain device model, battery levels for left/right earbuds and case, charging state, lid status, and color.

This is one of the richest BLE advertisement formats — it leaks detailed device state in the clear.

## BLE Advertisement Format

### Identification

- **Company ID:** `0x004C` (Apple Inc.)
- **TLV Type:** `0x07`
- **Minimum length:** 7 bytes

Found within Apple Continuity TLV chain (see `apple-continuity.md` for TLV parsing).

### Byte Layout (within TLV value)

```
Offset  Size  Field
------  ----  -----
0       1     Prefix/status byte
1–2     2     Device model (16-bit, big-endian: byte1 << 8 | byte2)
3       1     UTP (charging flags + status)
4       1     Battery: left (high nibble) + right (low nibble)
5       1     Battery: case (high nibble) + lid state (low nibble)
6       1     Color code
7+      var   Encrypted payload (optional)
```

### Device Model (bytes 1–2)

16-bit identifier assembled as `(byte[1] << 8) | byte[2]`:

| Model Code | Device |
|-----------|--------|
| `0x0220` | AirPods 1st Gen |
| `0x0F20` | AirPods 2nd Gen |
| `0x1320` | AirPods 3rd Gen |
| `0x0E20` | AirPods Pro |
| `0x1420` | AirPods Pro 2nd Gen |
| `0x0A20` | AirPods Max |
| `0x0320` | Powerbeats3 |
| `0x0B20` | Powerbeats Pro |
| `0x0C20` | Beats Solo Pro |
| `0x1120` | Beats Fit Pro |
| `0x1020` | Beats Studio Buds |
| `0x0520` | BeatsX |
| `0x0620` | Beats Solo3 |
| `0x0920` | Beats Studio3 |
| `0x1720` | Beats Studio Pro |
| `0x1220` | Beats Studio Buds+ |

Unknown models are reported as `Unknown (0xNNNN)`.

### UTP Byte (byte 3)

| Nibble | Bits | Meaning |
|--------|------|---------|
| High (charging flags) | Bit 0 | Left earbud charging |
| | Bit 1 | Right earbud charging |
| | Bit 2 | Case charging |
| Low | | Status/reserved |

### Battery Levels (bytes 4–5)

Each nibble encodes battery level as 0–10, multiply by 10 for percentage:

```
battery_left  = min((byte[4] >> 4) & 0x0F, 10) * 10   # 0–100%
battery_right = min( byte[4]       & 0x0F, 10) * 10   # 0–100%
battery_case  = min((byte[5] >> 4) & 0x0F, 10) * 10   # 0–100%
```

Values above 10 are clamped to 10 (100%).

### Lid State (byte 5, low nibble)

```
lid_open = (byte[5] & 0x0F) != 0
```

Non-zero indicates the AirPods case lid is open.

### Color (byte 6)

Device color identifier. Values are model-specific and not fully documented.

## Identity Hashing

```
identifier = SHA256("{mac}:{model_hex}:{first_7_bytes_hex}")[:16]
```

Includes the model and first 7 payload bytes to differentiate multiple AirPods from the same owner (e.g. AirPods Pro + AirPods Max).

## Raw Packet Examples

```
# AirPods Pro 2nd Gen, L=80% R=90% Case=60%, right charging, lid closed
4c 00 07 19 01 14 20 24 89 60 02 ...
│  │  │  │  │  │     │  │  │  └── color
│  │  │  │  │  │     │  │  └───── case=60%, lid=closed (0x0)
│  │  │  │  │  │     │  └──────── left=80%, right=90%
│  │  │  │  │  │     └─────────── UTP: charging_right=1
│  │  │  │  │  └───────────────── model: 0x1420 = AirPods Pro 2nd Gen
│  │  │  │  └──────────────────── prefix byte
│  │  │  └─────────────────────── length (25 bytes typical)
│  │  └────────────────────────── type (0x07 = Proximity Pairing)
│  └───────────────────────────── company ID high
└──────────────────────────────── company ID low (Apple)
```

## Privacy Implications

- Battery levels, charging state, and lid position are broadcast in the clear
- Model identification reveals the specific product a person owns
- Combined with Nearby Info from the paired phone, can link a person to their accessories
- Useful for presence detection: AirPods broadcasting = someone is nearby with earbuds

## References

- [furiousMAC/continuity — Proximity Pairing](https://github.com/furiousMAC/continuity/blob/master/messages/proximity_pairing.md)
- Martin et al., "Handoff All Your Privacy", PETS 2019
