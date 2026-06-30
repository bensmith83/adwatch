# Icetro commercial ice / beverage machine

## Overview

**Icetro** is a Korean manufacturer of commercial ice makers, soft-serve
and slush machines, and beverage dispensers. Its US arm, **Icetro
America**, is part of **Middleby Corporation**. Icetro units expose a BLE
interface (for an installer / service app) that advertises an OEM-set
**`ICETRO-<tokens>`** local name, backed by the **Nordic UART Service
(NUS)** for the actual data channel.

Without dedicated attribution the device lands in the generic
`nordic_uart_service` "custom" bucket — NUS is a generic serial-port
profile used by thousands of unrelated products, so the service UUID alone
says nothing about the vendor. The decisive signal here is the
manufacturer-set **`ICETRO-` name prefix**, which gives HIGH confidence on
the vendor. This parser upgrades the attribution while coexisting with the
generic NUS parser (the NUS UUID is reported as a confirmer, not the gate).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Local name | `ICETRO-<tokens>` | Prefix `ICETRO-` is the gate — e.g. `ICETRO-1906-550` |
| Service UUIDs | includes `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` | Nordic UART Service; confirmer, not gated |
| Manufacturer data | none | No mfg payload observed |
| Address type | `random` | RPA / random-static; rotates |

The **name prefix alone** is enough to match. The NUS UUID appears on the
fully-populated frame and is recorded as a confirmer
(`nordic_uart_service = yes/no`); a name-only secondary frame (no service
UUIDs) still matches on the prefix.

### Nordic UART Service caveat

`6E400001-B5A3-F393-E0A9-E50E24DCCA9E` is the **Nordic UART Service**, a
generic serial-over-BLE profile from the Nordic SDK. It is inherited from
the chipset / SDK, **not** registered by Icetro, and is shared by a huge
range of unrelated devices. So NUS alone is meaningless as an attribution;
the OEM-set `ICETRO-` name prefix is what identifies the vendor.

### What we can surface

| Field | Source | Notes |
|---|---|---|
| `vendor` | hard-coded | `Icetro` |
| `product` | hard-coded | `commercial ice / beverage machine` |
| `device_name` | localName | full advertised name, e.g. `ICETRO-1906-550` |
| `model_tokens` | localName | substring after `ICETRO-`, **raw / undecoded** (e.g. `1906-550`) |
| `nordic_uart_service` | serviceUUIDs | `yes` if the NUS UUID is present, else `no` |

#### `model_tokens` are deliberately raw

The `1906-550` tokens are **not confidently decoded**. There are no public
Icetro BLE docs and we have a single observed device, so we do **not**
assert that these encode a model number, machine size, manufacture date,
or anything else. They are surfaced verbatim as `model_tokens` so a future
capture with more units can correlate them — but the parser makes no
semantic claim about them.

### What we cannot surface

- Machine state, temperature, ice level, fault codes, runtime — these
  would require a GATT connection over the NUS TX/RX characteristics and
  Icetro's vendor-specific framing, which is undocumented.
- Any per-unit serial / hardware ID beyond the advertised name (no
  manufacturer data is emitted).

## Stable identity

The advertised local name is the only stable handle observed, so it is the
stable key:

```
stable_key = icetro:<localName>      (e.g. icetro:ICETRO-1906-550)
identifier = SHA256(stable_key)[:16]
```

This is a name-scoped identity: two units with distinct `ICETRO-` names
get distinct keys; the same name yields a stable key across the random
BLE-layer address rotation.

## Detection significance

- Flags commercial ice / beverage equipment (foodservice, hospitality,
  convenience retail) — a useful venue / site-type signal.
- The `ICETRO-` prefix is OEM-set, so vendor attribution is HIGH
  confidence even though there is no public feature-level BLE
  documentation.

## Confidence

- **Vendor: HIGH** — the `ICETRO-` local-name prefix is set by the OEM.
- **Feature decode: NONE** — no public BLE feature docs and a single
  observed device, so this is a **vendor-only fingerprint**. No telemetry
  is decoded (name-only attribution over a generic NUS channel), and the
  `1906-550` tokens are left raw / undecoded.

## References

- [Icetro America (Middleby)](https://www.icetro.us/) — commercial ice /
  beverage equipment manufacturer; OEM behind the `ICETRO-` name prefix.
- [Nordic UART Service (NUS) spec](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/libraries/bluetooth_services/services/nus.html)
  — UUID `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`, generic serial-over-BLE.
- Captures: `research/nearsight_export 7.json` (~19 sightings, 1 device,
  named + name-only frames).
