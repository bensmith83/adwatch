# Casambi Lighting Plugin

## Overview

Bluetooth SIG company ID `0x03C3` is registered to **Casambi Technologies Oy** (Espoo, Finland) — the maker of a widely-deployed Bluetooth mesh lighting-control ecosystem used in commercial offices, retail, hospitality, and museums. Casambi luminaires, drivers, and gateway modules (e.g. CBU-ASD, CBM-002 / CBM-003) form a self-healing BLE mesh and continuously emit manufacturer-specific advertisement frames carrying the mesh network identifier plus rolling per-luminaire fingerprint bytes.

The Casambi protocol is documented at a high level by the vendor (ECDH key exchange, AES-CTR encryption, CMAC authentication) but the on-air advertisement frame layout is not officially published. The fields exposed here are derived from passive captures and the open-source [`lian/esp32-casambi`](https://github.com/lian/esp32-casambi) reverse-engineering project.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Company ID | `0x03C3` (Casambi Technologies Oy) |
| Address type | random (rotates) |
| Frame variants | short (8 bytes total) and long (26 bytes total) |

We match purely on company ID. Casambi is the sole assignee of `0x03C3`.

### Manufacturer Data Layout — Long Frame (26 bytes, 24-byte payload)

```
c3 03 | XX XX XX XX XX XX | 76 3d 00 2c 00 00 | NN NN NN NN NN NN | RR | 2b | 00 48 f0
──┬── ────────────┬────────── ───────┬───────── ──────────┬─────────── ─┬ ──┬─ ─────┬─────
 CID  device fingerprint        fixed protocol         network ID    rolling fixed
LE 0x03C3        (6 bytes)         marker             (6 bytes)      counter footer
                                  `763D002C0000`     same across
                                                     mesh members
```

- **CID** (bytes 0..1): `c3 03` (little-endian `0x03C3`)
- **Device fingerprint** (bytes 2..7): per-luminaire identifier; differs between devices on the same mesh
- **Fixed protocol marker** (bytes 8..13): `76 3D 00 2C 00 00` in every captured long frame — likely a protocol/version constant
- **Network ID** (bytes 14..19): same 6-byte sequence across every member of a single Casambi mesh; the mesh's stable address
- **Rolling counter** (byte 20): low byte changes across consecutive captures of the same luminaire — likely a mesh-frame counter low byte
- **Fixed bytes** (byte 21): `2b` constant
- **Footer** (bytes 22..24): `00 48 f0` constant in every observed long frame

### Manufacturer Data Layout — Short Frame (8 bytes, 6-byte payload)

```
c3 03 | NN NN NN NN NN NN | RR
──┬── ──────────┬─────────── ─┬
 CID       network ID      rolling
LE 0x03C3   (same 6        counter
            bytes as long
            frames)
```

The short form omits the per-device fingerprint and protocol-marker block, leaving only the **mesh network ID** + 1 trailing byte. Both forms are emitted from the same mesh; long frames identify the luminaire, short frames identify the mesh itself.

### Stable Key

We hash the 6-byte **network ID** (when present) into the stable key — every member of a single Casambi mesh collapses to one key, which matches how the system is logically deployed (a mesh = a customer site). When only the device fingerprint is recoverable (long form), we additionally store it as `device_fingerprint_hex`.

```
casambi:<network_id_hex>
```

## Detection Significance

- **High-confidence vendor.** The SIG-assigned company ID is unique to Casambi, so there is no ambiguity about who made the broadcaster.
- **Site fingerprinting.** Multiple advertisements sharing the same 6-byte network ID localize all luminaires of a single commercial deployment to one stable key, which is more useful than the rotating BD_ADDR.
- **Commercial-lighting indicator.** Presence of Casambi traffic in a residential capture is unusual; it more commonly indicates an office, retail, or hospitality site nearby.

## What We Cannot Parse

- **Telemetry / payload contents.** Casambi traffic is AES-CTR encrypted end-to-end with per-mesh keys derived via ECDH; we can identify the mesh and individual luminaires by their constant header fields but cannot recover light state, dim level, scene index, etc.
- **Geographic / installation site.** The network ID is opaque; mapping it to a physical site requires out-of-band knowledge.

## References

- [Casambi — Casambi Mesh with Bluetooth Low Energy](https://casambi.com/casambi-mesh/)
- [Casambi System Overview (PDF, v3.1)](https://casambi.com/wp-content/uploads/2023/10/Casambi-System-Overview_EN_v3.1.pdf)
- [lian/esp32-casambi — offline ESP32 BLE controller for Casambi (reverse-engineered)](https://github.com/lian/esp32-casambi)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — `0x03C3` = Casambi Technologies Oy
- `research/adwatch_export 6.json` — 3 captured devices grouped onto one mesh
