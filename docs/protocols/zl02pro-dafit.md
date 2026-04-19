# ZL02PRO / DaFit-family Smartwatch Protocol

## Overview

"ZL02PRO" is a white-label round-face Bluetooth-calling smartwatch sold by
many re-sellers (Kronus, Shenzhen Vanssa, opmowatch, ...). Underlying
hardware is **Realtek RTL8763EWE** (BT 5.2 dual-mode SoC with audio DSP);
the companion Android/iOS app is **Da Fit** (not VeryFit).

A small number of proprietary BLE-layer constants (company ID, service UUID,
and service-data framing) are shared across all SKUs using this firmware.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `ZL02PRO` (and variants: `ZL0xx...`) | Stable model prefix |
| Company ID | `0xF0EF` (mfg data prefix) | **Not SIG-registered** |
| Service data UUID | `0xFEEA` | **Not SIG-registered** |
| DKR magic | ASCII `"DKR"` = `44 4B 52` | First 3 bytes of FEEA service data |

Note: `0xFEEA` is often mis-attributed to "Samsung". It is **not** in the
Bluetooth SIG assigned-numbers list; Samsung's SmartTag/Find UUIDs are
`0xFD59` / `0xFD5A`. The collision appears to be incidental.

## Ad Format

### Manufacturer Data

```
Offset  Bytes     Meaning
  0-1   ef f0     Company ID 0xF0EF (little-endian, unregistered)
  2-7   xx..xx    6 opaque bytes (observed: eaae5bd0962a)
```

### Service Data (UUID 0xFEEA)

```
Offset  Bytes        Meaning
  0-2   44 4B 52     ASCII "DKR" protocol magic
  3-N   xx..xx       vendor-proprietary state/counter bytes
```

Observed example: `44 4B 52 03 04 00 10` — after `DKR`, the trailing
`03 04 00 10` has not been decoded. Candidate interpretations (not
confirmed): protocol version (`03`), payload-type (`04`), and a short
counter or status word.

### What We Cannot Parse

- Heart rate, step count (requires GATT connect to DaFit characteristics)
- Firmware version
- Pairing PIN / user ID

## Detection Significance

- Cheap BT-calling smartwatch in range, most commonly paired with the
  Da Fit app
- Same BLE framing is used by other DaFit-SDK watches; we match the
  local-name prefix OR the FEEA+DKR signature

## Parsing Strategy

1. Match `^ZL0[0-9A-Z]{2,}` in `local_name`, OR
2. Service data under UUID `0xFEEA` whose first three bytes are `DKR`.
3. Emit `device_class="smartwatch"`, store trailing protocol payload as
   `protocol_payload_hex` for later analysis.

## Identity Hashing

```
identifier = SHA256("{mac}:zl02pro")[:16]
```

## References

- [Realtek RTL8763E product page](https://www.realtek.com/Product/Index?id=3742&cate_id=194)
- [Example ZL02Pro listing (Kronus / Made-in-China)](https://kronus.en.made-in-china.com/product/YZBtTjgbbpGe/China-Bt-Call-Smartwatch-Rtl8763ewe-One-Click-Connect-1-39-Inch-360-360-HD-Screen-Dafit-APP-Smartwatch-for-Men-Women.html)
- [Nordic bluetooth-numbers-database (SIG CIDs — 0xF0EF absent)](https://github.com/NordicSemiconductor/bluetooth-numbers-database/blob/master/v1/company_ids.json)
