# Acaia Coffee Scale Plugin

## Overview

Acaia makes precision Bluetooth coffee scales popular among specialty coffee enthusiasts. Models include Lunar, Pearl, Pyxis, and Cinco. They advertise over BLE for discovery and pairing. Acaia scales are frequently seen in coffee-focused households.

## Supported Models

| Model | Local Name | Notes |
|-------|-----------|-------|
| Lunar (v1) | `ACAIA` or `LUNAR_*` | Original lunar |
| Lunar (v2) | `LUNAR_*` | Updated model |
| Pearl | `PEARL_*` or `ACAIA_*` | Pour-over scale |
| Pearl S | `PEARLS_*` | Updated Pearl |
| Pyxis | `PYXIS_*` | Single-cup scale |
| Cinco | `CINCO_*` | Newer model |

## BLE Advertisement Format

### Identification

Acaia scales can be identified by:

1. **Local Name Pattern**: Starts with `ACAIA`, `LUNAR`, `PEARL`, `PYXIS`, or `CINCO`
2. **Service UUID**: `00001820-0000-1000-8000-00805f9b34fb` (Internet Protocol Support — used by some models) or custom Acaia UUIDs

Best match strategy: `local_name_pattern=r"(?i)^(ACAIA|LUNAR|PEARL|PYXIS|CINCO)"`.

### Advertisement Data

Acaia scales advertise:
- Local name with model and optional serial suffix
- Service UUIDs for discovery
- Manufacturer data varies by model generation

### GATT Service (for reference)

Main communication uses a custom service:
```
Service:        49535343-FE7D-4AE5-8FA9-9FAFD205E455
Write char:     49535343-8841-43F4-A8D4-ECBE34729BB3
Notify char:    49535343-1E4D-4BD9-BA61-23C647249616
```

Weight/flow data is streamed via GATT notifications (requires active connection).

### Parser Scope (Passive Only)

Since adwatch is a passive scanner, the parser extracts:
- Device model from local_name
- Device identifier from name suffix
- Model generation detection
- Presence detection

Note: Weight and flow data require an active GATT connection. The parser provides device identification and presence.

## References

- [pyacaia](https://github.com/lucapinello/pyacaia) — Python library for Acaia scales
- [AcaiaArduinoBLE](https://github.com/tatemazer/AcaiaArduinoBLE) — Arduino BLE client
- [LunarGateway](https://github.com/nicpottier/LunarGateway) — ESP32 gateway
