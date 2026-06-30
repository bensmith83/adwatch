# Rheem EcoNet smart HVAC / water heater

## Overview

**EcoNet** is Rheem's branded connected-equipment ecosystem. Rheem ships a
dedicated Bluetooth/BLE wireless module for EcoNet HVAC equipment (heat
pumps, AC condensers, furnaces / air handlers) and water heaters; the
equipment advertises over the **Nordic UART Service (NUS)** for provisioning
and pairs with the EcoNet mobile app.

These units advertise a **vendor-structured local name** that only the OEM
sets:

```
EcoNet-<UNIT>-<SERIAL>
```

so even though the radio is a generic Nordic-UART serial bridge, the name
gives a confident Rheem attribution plus the unit type and serial.

## Supported / observed unit types

| Token | Meaning |
|---|---|
| `ODU` | outdoor unit (heat pump / AC condenser) |
| `IDU` | indoor unit (air handler) |
| `FRN` | furnace / indoor air handler |
| `WH` | water heater |
| *other* | unknown unit type (still parsed: vendor + serial) |

The token map is kept open-ended; an unrecognized `<UNIT>` token still parses
with a generic description.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Local name | prefix `EcoNet-` | the decisive anchor (OEM-set) |
| Service UUID | `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` | Nordic UART Service — confirmer |
| Service UUID | `180A` | Device Information Service — also present |
| Manufacturer data | none | — |
| Address type | `random` | rotating; serial is the stable identity |

The parser matches on the `EcoNet-` **local-name prefix** (mirroring the
`IoTV` / `Lovense` NUS-family parsers) and reports the NUS UUID as a
confirmer. It **coexists** with the generic `nordic_uart_service` parser —
both results merge — upgrading the attribution from "Nordic Semiconductor /
custom / dev_board" to a real Rheem EcoNet HVAC identification.

### Name decode

`EcoNet-ODU-W392520787`
- `UNIT` = `ODU` → outdoor unit (heat pump / AC condenser)
- `SERIAL` = `W392520787` (literal `W` + digits; opaque per-unit serial)

`EcoNet-FRN-W512518423`
- `UNIT` = `FRN` → furnace / indoor air handler
- `SERIAL` = `W512518423`

### What we can surface

| Field | Source | Notes |
|---|---|---|
| `vendor` | hard-coded | `Rheem` |
| `product` | hard-coded | `EcoNet smart HVAC` |
| `unit_type` | localName | `ODU` / `FRN` / `WH` / … |
| `unit_description` | token map | human-readable unit type |
| `serial` | localName | per-unit serial (stable key) |
| `nordic_uart_service` | serviceUUIDs | `yes` / `no` confirmer |

### What we cannot surface

- Setpoints, mode, compressor/burner state, tank temperature, fault codes —
  all require the EcoNet app's authenticated GATT session (or the wired
  EcoNet bus; see esphome-econet prior art). The advertisement is name-only.

## Parser scope (passive only)

Identification + unit type + serial only. NearSight never connects.

## Stable identity

```
stable_key = rheem_econet:<serial>          (serial present)
stable_key = rheem_econet:name:<localName>  (no serial field)
identifier = SHA256(stable_key)[:16]
```

The serial survives the random-address rotation.

## Detection significance

- Identifies fixed residential/commercial HVAC and water-heating
  infrastructure — a strong "this is a dwelling/mechanical room" context
  clue, and persistent (an outdoor unit was seen 306× and a furnace 777× in
  a single capture).
- Upgrades a large generic-NUS bucket into a named-vendor attribution.

## References

- [Rheem EcoNet](https://www.rheem.com/econet/)
- [esphome-econet](https://github.com/esphome-econet/esphome-econet) — EcoNet protocol prior art (wired bus)
- [Nordic UART Service reference](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/libraries/bluetooth_services/services/nus.html)
- Captures: `research/nearsight_export 7.json` (2 units — ODU + FRN — 1083 sightings combined).
