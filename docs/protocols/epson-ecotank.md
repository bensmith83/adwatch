# Epson EcoTank Inkjet Printer

## Overview

Epson's **EcoTank** inkjet / photo printer line (ET-XXXX series) ships
with a BLE radio used by the Epson Smart Panel mobile app for initial
Wi-Fi onboarding. Once provisioned, day-to-day printing happens over
Wi-Fi → cloud or LAN, but the BLE advertiser stays on so the printer
remains discoverable to anyone passively scanning.

The advertisement is purely identifying — no ink levels, job state,
or maintenance status is exposed over BLE.

## Supported Models

Any Epson printer that advertises company ID `0x0040` and a local name
matching `ET-XXXX Series`. Confirmed observations:

| Local name | Family | Notes |
|------------|--------|-------|
| `ET-2800 Series` | EcoTank entry-level | All-in-one cartridge-free |
| `ET-8500 Series` | EcoTank Photo | 6-color photo printer |

Other ET-series models (ET-3850, ET-4850, ET-15000, ET-16650, ET-8550)
should also be picked up automatically by the same pattern.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0040` | Seiko Epson Corporation (Bluetooth SIG) |
| Service UUID | `802A0000-4EF4-4E59-B573-2BED4A4AC159` | Epson onboarding / Smart Panel service |
| Local name | `ET-XXXX Series` | Stable, identifies model family |

Regex: `^(ET-\d{3,4}) Series$`

### Manufacturer Data

```
Bytes:  40 00 | 00 | 66 02
        └─┬─┘   └┬┘   └─┬─┘
         cid    flag   model-token (varies per SKU)
```

Captured:

| Model | Payload |
|-------|---------|
| ET-8500 | `40 00 00 66 02` |
| ET-2800 | `40 00 00 6C 02` |

The 3 trailing bytes change per SKU. They almost certainly encode the
model family / sub-variant — `0x66` for ET-8500 vs `0x6C` for ET-2800
— but the full mapping has not been reverse-engineered. The parser
exposes the full payload as `payload_hex` for forensic comparison.

The same model on a different machine carries identical payload bytes
— so the manufacturer data does **not** distinguish individual units
on the same product line. There is no per-unit serial in the
advertisement; that lives behind the GATT setup service.

## Identity Hashing

```
identifier_hash = SHA256("epson_ecotank:{model}")[:16]
```

**Known limitation:** two ET-8500 units in the same room hash to the
same identity. There is no per-unit token in the advertisement, so
adwatch cannot disambiguate them passively. The user-facing UI should
treat this as "presence of an ET-8500 nearby" rather than "specific
printer X".

If finer identity is required, the Epson setup service exposes the
printer's serial number over a connected GATT session (out of scope
for adwatch's passive scanner).

## What We Cannot Parse Without GATT

- Per-unit serial number
- Ink levels (the headline EcoTank feature)
- Print-job queue / state
- Wi-Fi provisioning status
- Firmware version

All of those require an active GATT session against the Epson setup
service or the printer's network management API.

## References

- Bluetooth SIG company ID `0x0040` → Seiko Epson Corporation
- Epson Smart Panel app: https://www.epson.com/Support/wa00821
- EcoTank product line: https://epson.com/EcoTank
