# Google Fast Pair

## Overview

Google Fast Pair uses BLE service data with UUID `0xFE2C` to enable quick pairing of accessories with Android devices. **Important:** phones do NOT advertise Fast Pair — only **accessories** (headphones, speakers, earbuds) broadcast this protocol.

Fast Pair operates in two modes: Discoverable (pairing) and Not Discoverable (paired, advertising to nearby account holders).

## BLE Advertisement Format

### Identification

- **AD Type:** `0x16` (Service Data — 16-bit UUID)
- **Service UUID:** `0xFE2C` (little-endian: `2c fe`)
- **Source:** `service_data` dictionary, key `fe2c` or full 128-bit form

### Mode Detection

The first byte distinguishes modes:
- **Discoverable mode:** 3 bytes, first byte has upper nibble set (Model ID)
- **Not Discoverable mode:** flags byte with upper 4 bits = 0 (`0b0000UTLL`)

## Discoverable Mode (Pairing)

Broadcast when accessory is in pairing mode.

### Byte Layout

```
Offset  Size  Field
------  ----  -----
0–2     3     Model ID (24-bit, assigned by Google)
```

The Model ID is registered in Google's [Fast Pair device database](https://developers.google.com/nearby/devices). It identifies the specific product (e.g., "Pixel Buds Pro", "Sony WH-1000XM5").

### Detection Heuristic

```
if len(data) == 3 and (data[0] & 0xF0) != 0:
    # Discoverable mode — data is Model ID
```

## Not Discoverable Mode (Paired)

Broadcast when accessory is paired and within range of the owner's account.

### Byte Layout

```
Offset  Size  Field
------  ----  -----
0       1     Flags: 0b0000_UTLL
1–N     var   Account Key Filter (Bloom filter)
N+1     1–2   Salt (optional)
N+2+    var   Battery Data (optional)
```

### Flags Byte

```
Bits 0–1 (LL): Filter length encoding
Bit 2 (T):     Message type (0 = Account Key Filter)
Bit 3 (U):     UI indication
Bits 4–7:      Reserved (always 0)
```

Filter length encoding:

| LL | Filter Length |
|----|---------------|
| 0 | 0 bytes |
| 1 | 1 byte |
| 2 | 2 bytes |
| 3 | 4 bytes |

### Account Key Filter

Variable-length Bloom filter built from:
```
size = truncate(1.2 * n + 3)  # n = number of account keys
```

Each entry is `SHA256(Account_Key + Salt)`, inserted into the Bloom filter. This allows the owner's phone to recognize its accessories without revealing identity to others.

### Salt

1–2 bytes of random data, regenerated every ~15 minutes (synced with BLE MAC rotation).

### Battery Data (optional)

When present, contains battery levels for the accessory.

## Rotation Behavior

| Component | Rotation Interval |
|-----------|------------------|
| BLE MAC | ~15 minutes (RPA) |
| Account Key Filter | ~15 minutes (regenerated with new salt) |
| Salt | ~15 minutes |
| Model ID (discoverable) | Never (static per product) |

## Identity Hashing

**Discoverable mode:**
```
identifier = SHA256("{mac}:{model_id_hex}")[:16]
```

**Not Discoverable mode:**
```
identifier = SHA256("{mac}:{filter_hex}:{salt_hex}")[:16]
```

Note: Both rotate every ~15 minutes, making long-term tracking difficult by design.

## Limitations for Phone Counting

1. **Phones don't advertise Fast Pair** — only accessories do
2. Filter is intentionally designed to prevent tracking
3. Rotation synced with RPA (~15 min)
4. Useful for detecting *someone with Fast Pair earbuds nearby*, not specific people

## Raw Packet Examples

```
# Discoverable mode: Model ID 0xABCDEF (Pixel Buds Pro example)
Service UUID: fe2c
Data: ab cd ef
      └────── Model ID (3 bytes)

# Not Discoverable mode: 2-byte filter + 1-byte salt
Service UUID: fe2c
Data: 02 a1 b2 c3
      │  │     └── salt
      │  └──────── Account Key Filter (2 bytes)
      └─────────── flags: LL=2 (2-byte filter), T=0, U=0
```

## References

- [Google Fast Pair Specification](https://developers.google.com/nearby/fast-pair/specifications)
- [Fast Pair Device Database](https://developers.google.com/nearby/devices)
- [Bluetooth SIG — Service UUID 0xFE2C](https://www.bluetooth.com/specifications/assigned-numbers/)
