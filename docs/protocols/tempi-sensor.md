# Tempi (tempi.fi) Temperature/Humidity Sensor BLE Protocol

## Overview

**Tempi** (tempi.fi) makes Bluetooth wireless temperature/humidity data
loggers. Their advertisement is self-identifying in an unusually direct way:
the vendor encoded its own **domain name into the 128-bit service UUID**.

```
EFAA0000-7777-772E-7465-6D70692E6669
         └────────────── ASCII ──────────────┘
bytes:   77 77 77 2E 74 65 6D 70 69 2E 66 69
ASCII:    w  w  w  .  t  e  m  p  i  .  f  i     ->  "www.tempi.fi"
```

A domain-in-UUID is effectively unspoofable by accident, so this is a
zero-false-positive identifier.

## Identification

| Signal | Value | Notes |
|---|---|---|
| Service UUID (128-bit) | `EFAA0000-7777-772E-7465-6D70692E6669` | tail bytes spell `www.tempi.fi` |
| Local name | `T_<12 hex>` (e.g. `T_EE760AF5F96A`) | `T` + the device's own random-static BLE address; absent on some frames |
| Manufacturer data | `b965b686ac67` | 6-byte **constant** vendor signature (CID `0x65B9` is vanity/unregistered), NOT telemetry |
| Address type | random | |
| Device class | `sensor` | |

### Captured sample

```
serviceUUIDsJSON:   ["EFAA0000-7777-772E-7465-6D70692E6669"]
localName:          "T_EE760AF5F96A"   (nameless sibling frame also seen)
manufacturerDataHex: b965b686ac67
sightingCount:      2   (1 named + 1 nameless)
rssiMax:            -93 dBm
addressType:        random
```

## Match rule

Match any advertised serviceUUID whose lowercased string **contains the
`www.tempi.fi` byte suffix** `7777-772e-7465-6d70692e6669`. Matching the domain
bytes (rather than the full UUID) is robust to Tempi using a different leading
16-bit service selector (`EFAA0001…` etc.) on the same vendor base UUID. The
`T_` name is corroborating only — the UUID is the anchor; a `T_`-prefixed name
without the UUID does not claim.

## Scope — identity/labeler only

The advertisement carries **no decodable telemetry**: there is no service data,
and the manufacturer data is a 6-byte constant, not a temperature/humidity
field. Temperature and humidity are almost certainly read over a **GATT
connection**, not broadcast. This parser therefore **labels** the device
(vendor `Tempi`, product "Wireless Temperature/Humidity Sensor") and does not
invent readings. Metadata records the honest scope (`scope = identity_only …`).

## Stable key

```
tempi_sensor:<mac>
```

## Confidence

- **Attribution: HIGH.** The service UUID literally contains `www.tempi.fi`; the
  `T_<random-static-address>` name and the constant unregistered-CID mfr
  signature are all consistent with a small-vendor BLE sensor.
- **Sighting support: LOW** (2 sightings, 1 named). Shipped as an
  identity/labeler; revisit for value decoding only if GATT-side or
  multi-device captures appear.

## References

- [tempi.fi](https://tempi.fi/) — wireless temperature/humidity sensor vendor.
- Bluetooth SIG `company_identifiers.yaml` — `0x65B9` not present (above max
  ≈ `0x10E1`); the vendor identity rests on the domain-in-UUID, not the CID.
