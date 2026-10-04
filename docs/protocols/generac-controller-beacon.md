# Generac Generator-Controller Beacon (CID 0x0DA6)

## Overview

[Generac](https://www.generac.com/) makes home and commercial standby
generators; its Evolution-generation controllers and Mobile Link
accessories carry Wi-Fi/BLE radios so the Mobile Link app can set them up
and monitor them. Two units captured in the 2026-08-28 telemetry sweep
(2026-08-26, 21:14 and 23:44 UTC, from random addresses with no local name)
advertise a 26-byte manufacturer frame under CID `0x0DA6` — SIG-assigned to
**Generac Corporation** — whose body is two ASCII fields: a ten-digit
generator serial and a nine-character unit code. One unit's serial field
was ten `F`s, i.e. not yet provisioned. Both also listed the 128-bit
service UUID `02040000-D3A7-4B20-B612-1C53EF06AB71`; three further records
carried that UUID with no manufacturer data.

The vendor is certain (SIG registry). The product is inferred — a
controller broadcasting the generator's serial — and no Generac document
describes the frame, so it is recorded as "(probable)".

## Supported Models

| Model | Attribution | Notes |
|-------|-------------|-------|
| BLE-equipped generator controller (Evolution 2.0 / Mobile Link class) | probable | inferred from the vendor's product range and a generator serial in the frame; not named by the bytes |

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0DA6` (wire `a6 0d`) | Generac Corporation (SIG) |
| Manufacturer data | 26 bytes | 24-byte payload |
| Service UUID (128-bit list) | `02040000-D3A7-4B20-B612-1C53EF06AB71` | on every unit; corroboration, not routed |
| Local name | none | |
| Address | random | |

### Frame layout (manufacturer data, 26 bytes)

| Offset | Field | Size | Observed | Notes |
|--------|-------|------|----------|-------|
| 0–1 | company ID | 2 | `a6 0d` | |
| 2–3 | header | 2 | `01 04` | constant on both units; reported raw, **not** gated on |
| 4–13 | serial | 10 | ten ASCII digits, or ten ASCII `F` | Generac generator serials are ten-digit numbers; all-`F` = unset |
| 14–22 | unit code | 9 | nine upper-case ASCII alphanumerics, `L?D8P…` on both | per unit (the two differ in five of nine characters); meaning unknown |
| 23–25 | trailer | 3 | `00 00 15` | constant on both units; reported raw |

### Examples (serial and unit code synthetic; header, trailer and grammar real)

```
a6 0d | 01 04 | 33 30 31 32 33 34 35 36 37 38 | 4c 35 44 38 50 41 42 43 44 | 00 00 15
                "3012345678"                     "L5D8PABCD"
a6 0d | 01 04 | 46 46 46 46 46 46 46 46 46 46 | 4c 33 44 38 50 57 58 59 5a | 00 00 15
                "FFFFFFFFFF" (unset)             "L3D8PWXYZ"
```

## Parser Scope (passive-only)

NearSight's `generac` claims an advertisement when the company ID is
`0x0DA6`, the payload is exactly 24 bytes, the serial field is all digits
or all `F`, and the unit field is nine upper-case alphanumerics. Any other
`0x0DA6` frame shape stays unclaimed. It reports:

| Field | Source |
|-------|--------|
| `vendor` | `Generac Corporation` |
| `product` | `BLE-equipped generator controller (probable)` |
| `serial` | bytes 4–13 when digits — tagged **unique, stable** |
| `serial_unset` | `true` when the field is all `F` (then `serial` is absent) |
| `unit_code` | bytes 14–22 — tagged **unique, stable** |
| `header_hex`, `trailer_hex`, `payload_hex` | raw |
| `service_uuid` | `02040000-d3a7-…` when advertised |
| `attribution_note` | the reasoning above |

Identity: `stableKey = generac:<serial>`, or `generac:unit:<unit_code>`
while the serial is unset. Device class `energy`; beacon type
`generac_controller_beacon`.

## Privacy

A generator serial is a permanent, unit-unique identifier that a dealer or
warranty lookup can resolve to an installation address — and it is
broadcast in the clear from a BLE address that would otherwise rotate.
Anyone within range can tell that a specific standby generator is nearby,
across days, without any Generac account.

## What We Cannot Parse

- The header `01 04` and trailer `00 00 15`: frame type / version and a
  status byte are plausible readings; two units cannot tell a protocol
  constant from a per-install value.
- What the unit code is (controller id, Mobile Link module id, a pairing
  code) — the shared `L?D8P` prefix suggests a model or batch component.
- Generator state, run hours, alarms, fuel — nothing operational is in the
  frame.
- Whether the UUID-only records (no manufacturer data) are the same units
  in a different advertising phase or a different Generac product.

## References

- NearSight `research/sweep-2026-08-28-candidates.md` — the two-unit
  capture
- [Bluetooth SIG company identifiers](https://bitbucket.org/bluetooth-SIG/public/raw/HEAD/assigned_numbers/company_identifiers/company_identifiers.yaml) — `0x0DA6` Generac Corporation
- Generac Mobile Link / Evolution 2.0 controller product pages (Wi-Fi + BLE
  setup)
