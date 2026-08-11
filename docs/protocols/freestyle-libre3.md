# Abbott FreeStyle Libre 3 CGM

## Overview

The **Abbott FreeStyle Libre 3** is a continuous glucose monitor (CGM) — a
small body-worn sensor that streams interstitial glucose to a phone over BLE.
It is one of the most widely deployed CGMs, so its BLE advertisement is a
strong "medical wearable nearby" signal.

The sensor's BLE radio is the **EM Microelectronic-Marin EM9304** SoC (the
same family teardowns confirm in the Libre 2), but the *product* is Abbott's —
EM Micro is only the silicon.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Service UUID | `0898xxxx-EF89-11E9-81B4-2A2AE2DBCCE4` | the Libre 3 data-service family; `089810CC-…` is the advertised data service |
| Local name | `FreeStyle Libre 3` / `ABBOTT` / `LIBRE3` (prefix) | often present during pairing; absent on steady-state frames |
| Address type | `random` | rotating |

Either signal identifies the device: the parser matches the
`^0898[0-9a-f]{4}-ef89-11e9-81b4-2a2ae2dbcce4$` service-UUID pattern **or** an
`abbott` / `freestyle libre 3` / `libre3` local-name prefix.

> ⚠️ The UUID-v1 node `2A2AE2DBCCE4` in this UUID is a **generic, reused**
> UUID-v1 generator node (it also appears in unrelated projects, and in the
> CCC Digital Key `5810BBC0-…` UUID). It is **not** a vendor fingerprint — do
> not attribute by the node alone. The Libre 3 anchor is the full
> `0898xxxx-ef89-11e9-81b4-2a2ae2dbcce4` family (cross-checked below), or the
> Abbott/Libre local name.

### Why this UUID = Libre 3 (attribution)

The `0898xxxx-ef89-11e9-81b4-2a2ae2dbcce4` family is the FreeStyle Libre 3 data
service in ~20 independent CGM reverse-engineering projects, e.g.
`j-kaltes/Juggluco` (`LIBRE3_DATA_SERVICE`), `gui-dos/DiaBLE`
(`Libre3.swift case data`), `creepymonster/GlucoseDirect`,
`airedev326/LibreCRKit`, `EasyLars/Libre3Bridge`. The advertised data service
is `089810CC-…`; other Libre 3 GATT UUIDs share the `0898…/…2a2ae2dbcce4`
prefix/suffix.

### What we can surface

| Field | Source | Notes |
|---|---|---|
| `model` | hard-coded | `FreeStyle Libre 3` |
| `device_name` | localName | when present |
| `abbott_uuid` | serviceUUIDs | the matched `0898…` UUID |

### What we cannot surface

- Glucose readings, trend, sensor age, serial — all behind the encrypted,
  authenticated Libre 3 GATT session (the protocol the CGM RE projects
  implement requires pairing/keys). The passive advertisement is
  identification only.

## Parser scope (passive only)

Presence + model identification of a Libre 3 CGM. `deviceClass = medical`.

## Detection significance

- Flags a medical CGM wearable nearby — a sensitive presence signal (a person
  managing diabetes). Worth surfacing carefully in a privacy-aware app.

## Notes

- Registered on BOTH the `089810cc` data-service UUID and the Abbott/Libre
  local-name pattern. (A prior bug registered the parser by name only, so
  nameless Libre 3 frames advertising just the service UUID were mis-routed to
  a generic "unknown vendor" parser.)
- No live Libre 3 capture is present in the corpus that motivated this doc;
  byte-level specifics above are from the cited public RE projects, not a
  first-party capture.

## References

- [`j-kaltes/Juggluco`](https://github.com/j-kaltes/Juggluco) — `LIBRE3_DATA_SERVICE`
- [`gui-dos/DiaBLE`](https://github.com/gui-dos/DiaBLE) — `Libre3.swift`
- [`creepymonster/GlucoseDirect`](https://github.com/creepymonster/GlucoseDirect)
- FreeStyle Libre 2 teardown (EM Microelectronic EM9304 BLE SoC) — https://goughlui.com/2024/11/06/teardown-abbott-freestyle-libre-2-flash-glucose-monitoring-system-sensor/
