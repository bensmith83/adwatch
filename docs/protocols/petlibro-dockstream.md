# PETLIBRO Dockstream Plugin

## Overview

**PETLIBRO** (Shenzhen Libro Technology Co., Ltd.) ships WiFi/BLE-connected pet products — smart water fountains, automatic feeders, and litter accessories — that pair with the PETLIBRO mobile app and run on ESP8266/ESP32 silicon. The captured device in this codebase is the **Dockstream App-Monitoring Smart Pet Water Fountain**, model `PLWF105` (FCC ID `2A3DE-PLWF105`).

PETLIBRO SKUs follow the pattern `PL<family><digits>`:

| Family code | Product type | Example SKUs |
|---|---|---|
| `WF` | Water Fountain | `PLWF105` Dockstream Smart, `PLWF305` Dockstream RFID, `PLWF115`/`PLWF116` Dockstream variants |
| `AF` | Automatic Feeder | `PLAF103` Granary WiFi |
| other | Pet accessory | — |

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Manufacturer-data CID | `0xA398` (little-endian `98 a3`). **Outside the SIG-assigned range** (current SIG max ~ `0x10C7`) — a vanity / unregistered identifier. |
| Manufacturer payload | 4 bytes (shape resembles a counter / MAC suffix) |
| Service UUID (16-bit) | `FFEE` — a generic SIG-allocated UUID widely squatted by Chinese IoT vendors; not a strong attribution on its own. |
| Local name | The marketing SKU (e.g. `"PLWF105"`) |

### Attribution rule

The vanity CID `0xA398` is not assigned to PETLIBRO (or anyone) by the Bluetooth SIG, so it is unsafe to attribute on the CID alone. The PETLIBRO SKU pattern `^PL[A-Z]{2}\d+$` is distinctive but also could collide with unrelated devices. We therefore require **both** signals: the `0xA398` CID **and** a `PL<family><digits>` local name.

### Device-Class Heuristic

The two-letter family code drives device class:

- `WF` → `pet_water_fountain` (and a marketing-friendly `product_family` for SKUs whose marketing name we know — Dockstream Smart, Dockstream RFID).
- `AF` → `pet_feeder`.
- anything else → `pet_accessory`.

`stableKey` is `petlibro:<model>` (e.g. `petlibro:PLWF105`). The 4-byte manufacturer payload is surfaced as `payload_hex` for downstream observation; we have not reverse-engineered its semantics.

## Examples

| Capture | Inference |
|---|---|
| CID `0xA398` + name `PLWF105` + payload `16 4b ad ac` | model `PLWF105`, family `Dockstream Smart Fountain`, class `pet_water_fountain` |
| CID `0xA398` + name `PLWF305` | model `PLWF305`, family `Dockstream RFID Smart Fountain`, class `pet_water_fountain` |
| CID `0xA398` + name `PLAF103` | model `PLAF103`, class `pet_feeder` |
| name `PLWF105` only, no `0xA398` CID | rejected (CID required) |
| CID `0xA398` + name `iPhone` | rejected (PetLibro SKU shape required) |

## References

- [PETLIBRO Dockstream Smart Fountain pre-sale FAQ (PLWF105 / WF105)](https://designlibro.zendesk.com/hc/en-us/articles/44157653691033)
- [PETLIBRO PLWF105 vs PLWF305 model comparison](https://designlibro.zendesk.com/hc/en-us/articles/43976302757785)
- [FCC ID 2A3DE-PLWF105 (Shenzhen Libro Technology Co., Ltd.)](https://fccid.io/2A3DE-PLWF105)
- [Home Assistant community integration `jjjonesjr33/petlibro` (covers PLWF105 / PLWF305)](https://github.com/jjjonesjr33/petlibro)
- [ESPHome reverse-engineering firmware `taylorfinnell/petlibro-esphome`](https://github.com/taylorfinnell/petlibro-esphome)
