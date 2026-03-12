# Matter Commissioning

## Overview

Matter-compatible smart home devices broadcast BLE advertisements during commissioning (pairing) mode using service UUID `0xFFF6`. The payload contains a discriminator, vendor ID, and product ID that identify the specific device being set up.

Matter commissioning ads are **transient** — they only appear when a device is actively in pairing mode. Detecting them indicates someone is setting up a smart home device nearby.

## BLE Advertisement Format

### Identification

- **AD Type:** `0x16` (Service Data — 16-bit UUID)
- **Service UUID:** `0xFFF6` (little-endian: `f6 ff`)
- **Minimum length:** 8 bytes
- **Source:** `service_data` dictionary, key `fff6` or full 128-bit form

### Byte Layout (8 bytes)

```
Offset  Size  Field
------  ----  -----
0       1     OpCode (0x01 = Device Identification)
1–2     2     Discriminator (12-bit) + Advertisement Version (4-bit), little-endian
3–4     2     Vendor ID (16-bit, little-endian)
5–6     2     Product ID (16-bit, little-endian)
7       1     Flags
```

### OpCode (byte 0)

Only `0x01` (Device Identification) is processed. Other opcodes are ignored.

### Discriminator (bytes 1–2)

12-bit unique identifier for the pairing session:

```
raw = int.from_bytes(data[1:3], 'little')
discriminator = raw & 0xFFF          # lower 12 bits
advert_version = (data[2] >> 4) & 0x0F  # upper 4 bits of byte 2
```

The discriminator is set during manufacturing or setup and is used to match the device during commissioning. It appears in the device's QR code / manual pairing code.

### Vendor ID (bytes 3–4)

16-bit Connectivity Standards Alliance (CSA) assigned vendor identifier. Some known vendors:

| Vendor ID | Manufacturer |
|-----------|-------------|
| 0x1001 | (Test/development) |
| Various | Assigned by CSA |

### Product ID (bytes 5–6)

16-bit product identifier, assigned by the vendor. Unique per product model within a vendor's lineup.

### Flags (byte 7)

| Bit | Meaning |
|-----|---------|
| 0 | Has additional data |
| 1 | Is extended announcement |
| 2–7 | Reserved |

## Identity Hashing

```
identifier = SHA256("{mac}:{discriminator:03x}:{vendor_id:04x}:{product_id:04x}")[:16]
```

Combines MAC with all three identifying fields for a session-unique hash.

## Raw Packet Examples

```
# Matter device: discriminator=0x123, vendor=0x1001, product=0x0042, no flags
Service UUID: fff6
Data: 01 23 01 01 10 42 00 00
      │  │     │     │     └── flags (0x00)
      │  │     │     └──────── product_id (0x0042 LE)
      │  │     └────────────── vendor_id (0x1001 LE)
      │  └──────────────────── discriminator=0x123, version=0 (LE 16-bit)
      └─────────────────────── opcode (0x01 = Device Identification)

discriminator = 0x0123 & 0xFFF = 0x123 (291)
advert_version = (0x01 >> 4) & 0x0F = 0
```

## Detection Significance

- **Commissioning is temporary** — devices only broadcast during setup
- Detecting Matter commissioning means a smart home device is being paired *right now*
- Useful for home automation monitoring, security auditing, and device inventory
- The discriminator + vendor + product tuple can identify the specific device model

## References

- [Matter Specification](https://csa-iot.org/developer-resource/specifications-download-request/) (requires CSA membership)
- connectedhomeip/src/ble/BLEServiceData.h — `ChipBLEDeviceIdentificationInfo` struct
- [Project CHIP (now Matter) BLE documentation](https://github.com/project-chip/connectedhomeip)
