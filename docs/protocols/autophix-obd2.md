# Autophix OBD2 Diagnostic Scanner

## Overview

Autophix OBD2 scanners are automotive diagnostic tools that use BLE to bridge communication between a vehicle's OBD2 port and a smartphone app. They advertise using the generic `FFF0` service UUID and an Autophix-prefixed local name. Actual vehicle diagnostic data requires a GATT connection with ELM327-compatible AT commands.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `Autophix XXXX` pattern | e.g. `Autophix 3210`, suffix is the model number |
| Service UUID (advertised) | `fff0` | 16-bit generic custom service, shared by many BLE devices |
| Manufacturer data prefix | `a4c1383efaab` | Company ID `0xC1A4` |

The `FFF0` service UUID is extremely common across unrelated BLE devices. Identification must rely on the `local_name_pattern` in combination with the service UUID to avoid false matches.

### Manufacturer Data

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0-1 | 2 bytes | Company ID | `0xC1A4` (little-endian: `a4c1`) |
| 2-5 | 4 bytes | Device data | `383efaab` — purpose unknown, possibly a serial or hardware ID |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | local_name | Autophix OBD2 scanner nearby |
| Device model | local_name suffix | e.g. `3210` from `Autophix 3210` |

### What We Cannot Parse (requires GATT)

- Vehicle diagnostic trouble codes (DTCs)
- Engine RPM, speed, coolant temperature, etc.
- Vehicle VIN
- Battery voltage
- Live sensor data streams
- Freeze frame data

## Local Name Pattern

```
Autophix {model}
```

Examples: `Autophix 3210`, `Autophix V007`

The model number identifies the specific Autophix scanner product.

## Device Class

```
automotive
```

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

## Detection Significance

- Automotive diagnostic tool — indicates a vehicle with an active OBD2 scanner plugged in
- Common in mechanic shops, fleet management, and DIY vehicle diagnostics
- ELM327-compatible protocol over BLE GATT (service `FFF0`, characteristics for TX/RX)
- Device advertises whenever powered on via the vehicle's OBD2 port

## References

- [Autophix](https://www.autophix.net/) — manufacturer product line
- [ELM327 Protocol](https://www.elmelectronics.com/ic/elm327/) — OBD2 to serial interface standard
