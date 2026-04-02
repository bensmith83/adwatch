# Linksys WiFi Router / Mesh System

## Overview

Linksys WiFi routers and mesh systems broadcast BLE advertisements for initial device setup via the Linksys app. They are manufactured by Belkin International, which acquired the Linksys brand. BLE is used to discover and configure the router during first-time setup, after which the device continues to advertise at a low rate.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `Linksys` | Exact match |
| Service UUID (advertised) | `00002080-8eab-46c2-b788-0e9440016fd1` | 128-bit custom Linksys service |
| Manufacturer data prefix | `5c000101` | Company ID `0x005C` (Belkin International) |

The combination of the Belkin International company ID (`0x005C`) and the custom 128-bit service UUID is distinctive to Linksys networking products.

### Manufacturer Data

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0-1 | 2 bytes | Company ID | `0x005C` — Belkin International (little-endian: `5c00`) |
| 2-3 | 2 bytes | Device type / flags | `0x0101` — likely a product identifier or protocol version |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | local_name or service_uuids | Linksys router nearby |
| Manufacturer | company_id `0x005C` | Belkin International / Linksys |

### What We Cannot Parse (requires GATT)

- Router model (Velop, MR series, E series, etc.)
- Firmware version
- Network configuration state
- WiFi SSID or channel information
- Setup status

## Device Class

```
router
```

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

Linksys routers typically use a static BLE MAC address, making this a stable identifier.

## Known Models

| Model | Product | Notes |
|-------|---------|-------|
| Velop | Linksys Velop Mesh | Tri-band mesh WiFi system |
| MR series | Linksys MR7500, MR9600 | Gaming / high-performance routers |
| E series | Linksys E7350, E9450 | Consumer WiFi 6 routers |

## Detection Significance

- Network infrastructure device — indicates a home or office WiFi deployment
- BLE advertisement reveals presence of networking equipment
- Linksys app uses BLE for zero-conf setup before WiFi is configured
- Continuous low-rate advertising even after setup is complete

## References

- [Linksys Support](https://www.linksys.com/support) — manufacturer support
- [Bluetooth SIG Company Identifiers](https://www.bluetooth.com/specifications/assigned-numbers/) — Belkin International `0x005C`
