# StickNFind / snfBeacon Plugin

## Overview

[StickNFind](https://web.archive.org/web/2020*/sticknfind.com) (Sunrise, FL) shipped the original "Stick-N-Find" Bluetooth stickers and later released the Enterprise Beacon line ("snfBeacon" protocol — long battery life, temperature sensing, IP-67 enclosure). Their Bluetooth SIG company ID is `0x00F9`.

Two product variants are observed sharing this company ID, distinguishable by their proprietary 128-bit service UUIDs and local-name prefixes — almost certainly two SKUs from the same firmware base:

| Family | Service UUID | Local name prefix |
|---|---|---|
| Bfs ("Beacon Fleet Sensor"?) | `B4EF9336-D976-4740-A450-4800A79F9FCE` | `Bfs` |
| snfBeacon | `BEC26202-A8D8-4A94-80FC-9AC1DE37DAA6` | `tis` / `tin` |

The snfBeacon variant includes the ASCII magic `bcn` (`0x62 0x63 0x6E`) in its telemetry payload, which is what gives the protocol its informal name and what we look for as positive confirmation.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x00F9` | StickNFind (early SIG member). |
| Service UUID | `B4EF9336-…` or `BEC26202-…` | Distinguishes Bfs vs. snfBeacon variant. |
| Local name | `^(Bfs|tis|tin)[0-9A-Fa-f]{2}$` | Prefix + rolling 2-hex-char short ID. |

Bluetooth SIG company identifiers list `0x00F9 = StickNFind` ([YAML mirror](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)).

### Manufacturer Data Layout

```
Byte 0..1 : f9 00         — company ID 0x00F9 (LE)
Byte 2    : FT            — frame type
Byte 3..8 : UU UU UU UU UU UU   — 6-byte stable unit serial
Byte 9+   : trailer       — variant-specific telemetry / heartbeat block
```

Three frame types are observed:

| `FT` | Approx. length | Meaning |
|---|---:|---|
| `0x15` | 26 bytes | Full telemetry frame (most common). |
| `0x01` | 22 bytes | Alternate frame (heartbeat/connection-mode). |
| `0x06` | 8 bytes | Short heartbeat ping (no full serial). |

The short heartbeat (frame `0x06`) is too compact to carry the 6-byte serial; only the first ~5 payload bytes are present, so the parser surfaces the raw payload but cannot key the sighting back to a specific unit.

### Stable Identity

The 6-byte serial at payload offset 1..6 is **the** stable identifier for the physical beacon. It does not change across reboots, MAC rotations, or firmware updates — it is the right field to use as the device's primary key.

The two-hex-character suffix in the local name (e.g. `BfsB0`, `tisCC`) is a **rolling short ID** that changes between consecutive advertisements of the same physical unit. Do not use it as an identifier.

### snfBeacon "bcn" Magic

The `tis` / `tin` variant's telemetry frame embeds the ASCII bytes `bcn` (`0x62 0x63 0x6E`) at a fixed offset inside the trailer. The parser detects this magic and exposes `bcn_magic_present = true` when found, confirming we're looking at the documented snfBeacon protocol.

Examples:

| Local name | Mfg data (hex) | Family | Serial |
|---|---|---|---|
| `tisCC` | `f900151c74a03fc2e5071b62636e0001000000603d0020603d00` | snfBeacon | `1c74a03fc2e5` |
| `tisB0` | `f9001574eee908f536beca62636e0001000000603d0020603d00` | snfBeacon | `74eee908f536` |
| `Bfs9A` | `f900155b59a9f76e7130d3150020800d0020a02f5d000b000000` | Bfs | `5b59a9f76e71` |
| `BfsB0` | `f90015cb91e1075b87d403150020800d0020a52f5d000b000000` | Bfs | `cb91e1075b87` |

### Trailer Bytes

The trailer past the serial is partially decoded:

- `Bfs` family frame `0x15`: `<HW rev byte> 03 15 00 20 80 0d 00 20 XX YY 5d 00 0b 00 00 00`. The `XX YY` pair varies per unit; the `03 15 00 20 80 0d 00 20` stretch is constant across all units.
- `snfBeacon` family frame `0x15`: `1b 62 63 6e 00 01 00 00 00 60 3d 00 20 60 3d 00`. The `1b` byte is constant across all units; `62 63 6e` = ASCII "bcn".

We surface the full payload as `payload_hex` for further investigation but do not claim to decode every byte.

## Detection Significance

- **Asset-tracking deployments.** A site with dozens of StickNFind beacons typically uses them for indoor asset location (pallets, IT gear, healthcare equipment). The 6-byte serial is the asset ID.
- **Persistent tracking.** The serial is unauthenticated and stable forever, so anyone walking past a fixed installation can fingerprint individual assets across days. This is a real privacy property of the protocol.
- **No site-wide shared secret.** In our 24h capture each physical beacon broadcasts only its own unique serial; the 6-byte block is **not** a shared installation key. (We initially suspected one because the tis/tin family's serials cluster around a small set of MACs, but the 1:1 device-to-serial mapping holds.)

## What We Cannot Parse from Advertisements

- Temperature, battery, button events — the Enterprise Beacon supports these but they are likely behind a GATT characteristic, not in the advertisement.
- The semantic meaning of the variable trailer bytes — we have not validated.

## References

- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
- [StickNFind Enterprise Beacon press release](https://www.prnewswire.com/news-releases/sticknfind-introduces-enterprise-beacon-featuring-3-year-battery-temperature-sensing-and-waterproof-design-231735421.html)
- [StickNFind CES 2014 Beacon Developer Kit press release](https://www.prnewswire.com/news-releases/sticknfind-demonstrates-connected-applications-at-ces-2014-with-beacon-developer-kit-for-popular-bluetooth-stickers-239041701.html)
