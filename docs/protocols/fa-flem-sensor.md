# "FA-FLEM" Self-Identified Sensor (tentatively a BMW temperature probe)

## Overview

A BLE sensor observed in the 2026-07-06 sweep, identified by a **custom 128-bit
vendor UUID** `35CD221C-02B4-4D1F-9B54-6089C861AD62`. A random 128-bit UUID is
globally unique to whoever minted it, so keying on the full string is a
near-zero-false-positive anchor. **Low-trust-sourced.**

## ⚠️ Attribution is tentative

The localName `FA-FLEM-BMWTEMP-BR01` *suggests* a BMW temperature probe
("BMWTEMP", "BR01" ≈ board-rev 01, "FA-FLEM" ≈ an owner/fleet naming scheme),
but that string is **attacker-controllable DATA**, and the custom UUID is not
in any public registry. We therefore do **not** claim BMW as a confirmed
vendor — the parser records the honest, tentative label so future evidence can
firm it up.

## Identification

| Signal | Value | Notes |
|---|---|---|
| Service UUID (128-bit) | `35CD221C-02B4-4D1F-9B54-6089C861AD62` | custom vendor UUID — the attribution anchor |
| Service data `0x252A` | `58 d6 1f 4c ad a5` | 6-byte MAC-like **stable device id** |
| Service data `0x2120` | `0b` | opaque 1-byte counter (named variant only) |
| Local name | `FA-FLEM-BMWTEMP-BR01` | present on one of two frames; untrusted |
| Manufacturer data | none | |
| Device class | `sensor` | |

## Match rule

Match on the custom vendor UUID (case-insensitive). Stable key = the `252A`
device id (so both frames of one device map together, MAC-rotation-proof).
Byte-semantic decode deferred (one physical device, 15 sightings). Parser:
`FAFlemSensorParser` (`fa_flem_sensor`).
