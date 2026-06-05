# Nordic UART Service (NUS) — Generic Serial-over-BLE

## Overview

The **Nordic UART Service (NUS)** is a Nordic-defined GATT profile that
exposes a bidirectional, raw-byte serial channel over BLE. It is **not**
a vendor signature: Nordic published the UUIDs as a reference profile,
and the wider community adopted them as the de-facto "transparent UART"
service for dev boards, hobbyist firmware, JavaScript REPLs, and any
project that needs a phone↔MCU serial pipe without rolling its own GATT
spec.

The advertisement itself carries **no payload** — only the NUS 128-bit
service UUID announces "you can talk serial to me." All real data flows
over a connection, written into the RX characteristic and notified back
over the TX characteristic. Because so many ecosystems share the same
service UUID, this parser is structured as a **classifier**: it bridges
from "anonymous NUS device" to "likely <family>" by inspecting the
advertised local name.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` | NUS service (Nordic-defined, not BT SIG-registered) |
| Local name | family-specific prefix (see table) | Optional; absent on some bare firmware |
| Manufacturer data | (absent) | NUS adverts carry no payload |
| Service data | (absent) | — |
| Address type | typically `random` | Most dev boards rotate the address each boot |

The NUS profile additionally defines two characteristics on the service
(not visible in the advertisement, only after connection):

| Characteristic | UUID | Direction |
|----------------|------|-----------|
| RX | `6E400002-B5A3-F393-E0A9-E50E24DCCA9E` | host → device (write / write-without-response) |
| TX | `6E400003-B5A3-F393-E0A9-E50E24DCCA9E` | device → host (notify) |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Protocol | hard-coded | `nordic_uart_service` |
| NUS service UUID | hard-coded | `6E400001-...` |
| Device family | `localName` regex | one of the buckets in the family table |
| Vendor | derived from family | `Nordic Semiconductor` for generic / unknown; otherwise the family vendor |
| Device class | derived from family | usually `dev_board`; `environmental_sensor` for Ruuvi, `toy` for Pybricks |
| Device name | `localName` | preserved verbatim when present |

### What We Cannot Parse from the Advertisement

- The actual serial traffic — that needs a GATT connection and a subscribe
  to the TX characteristic.
- Firmware version, board revision, MCU SKU.
- Any application-level identity (Espruino board UID, Particle device ID,
  CircuitPython USB serial, etc.) — these live behind the connection or
  are simply not exposed at all.

## Stable Identity

If the advertisement includes a local name, use it as the stable key:

```
stable_key = nordic_uart_service:<localName>
```

Local names on NUS devices are typically user-settable or board-fixed
(e.g. `Puck.js abcd` derives `abcd` from the MAC tail, `Argon-abc` is a
Particle-assigned suffix). They are not guaranteed unique, but they
survive MAC rotation in practice for the documented families.

If the advertisement has no local name, fall back to the rotating MAC:

```
stable_key = nordic_uart_service:mac:<mac>
```

This is intentionally weak — a truly anonymous NUS device cannot be
re-identified across a private-address rotation from advertisement data
alone.

## Detection Significance

- Strong signal of a **hobbyist / developer environment**: maker space,
  engineer's desk, robotics lab, classroom.
- Often clustered: someone with one Adafruit Feather usually has several;
  Espruino users typically own a Puck and a Pixl; CircuitPython boards
  tend to come in batches.
- A single very-stationary NUS device with `-30 dBm` to `-50 dBm` RSSI
  usually means the observer's own dev board sitting on the bench.
- Combined with other Nordic-published profiles (DFU `FE59`, Thingy:52
  service UUIDs) it indicates a Nordic-SDK-based product, but NUS alone
  does **not** imply the device was built by Nordic.

## Known Device Families

The classifier matches the local name against the following prefixes
(case-sensitive, anchored at start). First match wins.

| localName pattern | Family bucket | Vendor | Device class | Notes |
|-------------------|---------------|--------|--------------|-------|
| `^Bluefruit` or `^AdaFruit` | `adafruit_bluefruit` | Adafruit | `dev_board` | Bluefruit LE Friend, Feather nRF52 with Bluefruit firmware |
| `^CIRCUITPY` | `circuitpython` | Adafruit | `dev_board` | CircuitPython BLE-UART boilerplate |
| `^CircuitPython` or `^mpy-uart` | `circuitpython` | CircuitPython / MicroPython | `dev_board` | MicroPython `aioble` / CircuitPython examples |
| `^Puck.js`, `^Pixl.js`, `^MDBT42Q`, `^Bangle.js` | `espruino` | Espruino | `dev_board` | JavaScript REPL over NUS |
| `^Nordic_UART` or `^Zephyr` | `nordic_sample` | Nordic Semiconductor | `dev_board` | Default nRF Connect SDK `peripheral_uart` sample |
| `^Particle-`, `^Argon-`, `^Boron-`, `^Xenon-` | `particle_io` | Particle | `dev_board` | Particle "Beginner BLE NUS" blueprint |
| `^Ruuvi ` | `ruuvi_nus` | Ruuvi Innovations | `environmental_sensor` | RuuviTag firmwares that expose NUS in addition to the manufacturer broadcast |
| `^Pybricks` | `pybricks` | Pybricks / LEGO | `toy` | Pybricks custom firmware for LEGO SPIKE / MINDSTORMS hubs |
| any other non-empty localName | `custom` | Nordic Semiconductor | `dev_board` | Named NUS device with no recognized prefix |
| (no localName) | `unknown` | Nordic Semiconductor | `dev_board` | Bare NUS advertisement, family indeterminate |

Family choices are deliberately conservative — only patterns that map
to a single, documented project are bucketed; anything else falls into
`custom`.

## References

- Nordic `peripheral_uart` sample — <https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/samples/bluetooth/peripheral_uart/README.html>
- Adafruit Bluefruit LE UART Friend — <https://learn.adafruit.com/introducing-the-adafruit-bluefruit-le-uart-friend/uart-service>
- Espruino BLE UART — <https://www.espruino.com/BLE+UART>
- Particle BLE NUS blueprint — <https://blueprints.particle.io/blueprint-beginner-ble-nus/>
- Ruuvi NUS docs — <https://docs.ruuvi.com/communication/bluetooth-connection/nordic-uart-service-nus>
- Pybricks firmware — <https://pybricks.com/>
- Capture: `research/nearsight_export.json` — single `Claude-8E32` dev
  board, 464 sightings, RSSI -34 to -99, classified as `custom`.
