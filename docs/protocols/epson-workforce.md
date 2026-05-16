# Epson WorkForce Pro Inkjet Printer

## Overview

Epson's **WorkForce Pro** inkjet printer line (WF-XXXX series) ships
with a BLE radio used by the Epson Smart Panel mobile app for initial
Wi-Fi onboarding. Once provisioned, printing happens over Wi-Fi → LAN
or cloud, but the BLE advertiser stays on so the printer remains
discoverable to anyone passively scanning.

WorkForce Pro is the office-class sibling of the consumer **EcoTank**
(ET-XXXX) line — see `epson-ecotank.md`. Both lines use Epson's company
ID `0x0040` and the same 802A0000-... onboarding service family, but
differ in the **last hex digit** of the service UUID:

| Product line  | Service UUID                                | Name regex            |
|---------------|---------------------------------------------|-----------------------|
| EcoTank (ET-) | `802A0000-4EF4-4E59-B573-2BED4A4AC159`      | `^ET-\d{3,5} Series$` |
| WorkForce (WF-) | `802A0000-4EF4-4E59-B573-2BED4A4AC158`    | `^WF-\d{3,4} Series$` |

The advertisement is purely identifying — no ink levels, toner state,
job queue, or maintenance status is exposed over BLE.

## Supported Models

Any Epson WorkForce printer that advertises company ID `0x0040` and a
local name matching `WF-XXXX Series`. Confirmed observation:

| Local name | Family | Notes |
|------------|--------|-------|
| `WF-3820 Series` | WorkForce Pro entry | Color all-in-one (print/scan/copy/fax) |

Other WF-series models (WF-2960, WF-4830, WF-7840, WF-C4810, WF-C8690,
etc.) should be picked up automatically by the same regex.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0040` | Seiko Epson Corporation (Bluetooth SIG) |
| Service UUID | `802A0000-4EF4-4E59-B573-2BED4A4AC158` | Epson WorkForce onboarding service |
| Local name | `WF-XXXX Series` | Stable, identifies model family |

Regex: `^(WF-\d{3,4}) Series$`

### Manufacturer Data

```
Bytes:  40 00 | 00 | 5A 02
        └─┬─┘   └┬┘   └─┬─┘
         cid    flag   model-token (varies per SKU)
```

Captured:

| Model | Payload |
|-------|---------|
| WF-3820 | `40 00 00 5A 02` |

The 3 trailing bytes change per SKU and almost certainly encode the
model family / sub-variant — `0x5A` for WF-3820, distinct from the
EcoTank tokens (`0x66` ET-8500, `0x6C` ET-2800, `0x68` ET-4850). The
full mapping has not been reverse-engineered. The parser exposes the
full payload as `payload_hex` for forensic comparison.

The same model on a different physical printer carries identical
payload bytes — so the manufacturer data does **not** distinguish
individual units on the same product line. There is no per-unit serial
in the advertisement; that lives behind the GATT setup service.

## Identity Hashing

```
identifier_hash = SHA256("epson_workforce:{model}")[:16]
```

**Known limitation:** two WF-3820 units in the same room hash to the
same identity. There is no per-unit token in the advertisement, so
adwatch cannot disambiguate them passively. The user-facing UI should
treat this as "presence of a WF-3820 nearby" rather than "specific
printer X".

If finer identity is required, the Epson setup service exposes the
printer's serial number over a connected GATT session (out of scope
for adwatch's passive scanner).

## What We Cannot Parse Without GATT

- Per-unit serial number
- Ink / toner levels
- Print-job queue / state
- Wi-Fi provisioning status
- Firmware version
- Fax line status (WF series specific)

All of those require an active GATT session against the Epson setup
service or the printer's network management API.

## References

- Bluetooth SIG company ID `0x0040` → Seiko Epson Corporation
- Epson Smart Panel app: https://www.epson.com/Support/wa00821
- WorkForce Pro product line: https://epson.com/For-Work/Printers/Inkjet/c/w12
- Sibling line: `epson-ecotank.md`
