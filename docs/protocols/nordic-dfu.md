# Nordic Semiconductor DFU Service

## Overview

Service UUID `0xFE59` (and the legacy UUID `00001530-1212-efde-1523-785feabcd123`) identifies devices using Nordic Semiconductor's BLE stack with Device Firmware Update (DFU) capability. This is not a single product — it's a platform used by hundreds of IoT devices including ThermoPro sensors, Hatch sound machines, fitness trackers, and many others.

Detecting `0xFE59` in advertisements tells you a Nordic-based IoT device is nearby, but not what kind.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFE59` | Nordic Semiconductor ASA (BLE SIG assigned) |
| Service UUID | `00001530-1212-efde-1523-785feabcd123` | Legacy Nordic DFU Service |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Nordic-based device present | service_uuid match | IoT device nearby |
| Possibly in DFU mode | service_uuid `0xFE59` prominent | May be updating firmware |

### Disambiguation

`0xFE59` alone is not enough to identify the device type. Combine with:
- **Local name** — ThermoPro, Hatch, etc. have distinctive names
- **Other service UUIDs** — device-specific services alongside Nordic DFU
- **Manufacturer data** — company ID reveals the actual vendor

## Devices Observed Using Nordic DFU

| Device | Additional Signals |
|--------|-------------------|
| ThermoPro sensors | local_name `TP3xxS (XXXX)`, company_id low byte `0xC2` |
| Hatch Baby Rest | local_name `* Hatch`, UUIDs `0224xxxx`/`0226xxxx` |
| Various fitness trackers | manufacturer-specific company IDs |
| Smart home devices | various custom service UUIDs |

## Detection Significance

- Very common — Nordic is the most popular BLE SoC platform
- Alone, indicates a generic IoT device
- When combined with other signals, helps narrow down the device category
- A device advertising `0xFE59` prominently (without other services) may be in firmware update mode

## References

- [Nordic Semiconductor — DFU](https://infocenter.nordicsemi.com/topic/sdk_nrf5_v17.1.0/lib_bootloader_dfu.html)
- [Bluetooth SIG — Service UUID 0xFE59](https://www.bluetooth.com/specifications/assigned-numbers/) (assigned to Nordic Semiconductor ASA)
