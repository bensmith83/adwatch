# Keiser M3i Indoor Cycle BLE Protocol

## Overview

The **Keiser M3i** is a widely-deployed commercial indoor cycle (spin bike).
In the 2026-07-06 trusted corpus it was the **single most-present unattributed
device** — localName `M3iS#000`, **982 sightings** — caught only by the generic
`generic_fitness_machine` SIG-profile parser. This parser is a
vendor-attribution **upgrade**: it labels the device as a Keiser M3i while
coexisting with the generic fitness parser (both match; their results merge —
the same pattern `IcetroParser` uses alongside the generic Nordic-UART parser).

## Identification

| Signal | Value | Notes |
|---|---|---|
| Local name | `M3i…` (observed `M3iS#000`) | Keiser's M-series indoor-cycle designation; `#<n>` ≈ bike number |
| Service UUIDs | `1826` (FTMS), `1818` (Cycling Power), `1816` (Cycling Speed & Cadence), `180A` (Device Info) | standard SIG fitness services |
| Manufacturer data | none | |
| Address type | random | |
| Device class | `fitness_equipment` | matches the generic fitness parser |

## Match rule

- localName prefix `M3i` **AND** at least one cycling/fitness SIG service
  (`1826` / `1818` / `1816`). The service requirement stops a random `M3i…`-named
  non-bike from claiming on the short name alone.
- Surfaces `vendor: Keiser`, `product: M Series indoor cycle (M3i)`, the raw
  `device_name`, and `model_tokens` (the part after `M3i`, e.g. `S#000`).

## Scope

**Identity/labeler only.** The advertisement carries no manufacturer/service
data — live metrics (power, cadence, gear, HR) are read over a **GATT
connection** to the FTMS / Cycling Power services, not broadcast. So this parser
attributes the vendor/model and does not decode live values.

Confidence: HIGH — the `M3i` model designation combined with the spin-bike SIG
service profile is a strong joint signal. Trusted-sourced (not low-trust).

## References

- Keiser M Series indoor cycles — FTMS / Cycling Power BLE profile.
- Parser: `KeiserM3iParser` (`keiser_m3i`); upgrade over `generic_fitness_machine`.
