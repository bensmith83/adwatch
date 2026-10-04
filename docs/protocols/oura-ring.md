# Oura Ring Plugin

## Overview

Bluetooth SIG company ID `0x02B2` is registered to **Oura Health Oy** (Finland), maker of the Oura Ring sleep / readiness tracker. The Ring exposes a proprietary primary service UUID `98ED0001-A541-11E4-B6A0-0002A5D5C51B` used by the Oura companion app for syncing nightly biometric data.

## BLE Advertisement Format

| Signal | Value |
|---|---|
| Company ID | `0x02B2` |
| Service UUID | `98ED0001-A541-11E4-B6A0-0002A5D5C51B` |
| Local name | `"Oura Ring 4"`, etc. |

### Manufacturer Data Layout (4 bytes after company ID)

```
Byte 0  : 0x04   — frame type (ring advertising)
Byte 1  : generation byte
Bytes 2..3: protocol / firmware revision (LE uint16, observed 0x0127)
```

### Generation Byte

From name-matched NearSight corpus captures (2026-09-29):

| Code | Generation | Example frame (after CID `b2 02`) |
|---|---|---|
| `0x40` | Gen 3 | `04 40 5a 06` — "Oura Ring Gen3" |
| `0x60` | Ring 4 | `04 60 5b 01` — "Oura Ring 4" |
| `0x70` | Ring 5 | `04 70 1b 01` — "Oura Ring 5" |

One unnamed capture carried `0x62` (`04 62 18 01`); left undecoded. Bytes
2..3 behave as a small LE counter (Ring 4: `0x0118`-`0x015C`, constant
high byte `0x01`), consistent with a firmware / protocol revision.

### Correction (2026-09-30): no hwtype/mode nibbles

The `oura` plugin v1.0 decoded byte 1 as `hwtype << 4 | mode` and bytes 2-3
as colour / battery / design nibbles, using enum tables from the decompiled
app (GEN3=1, GEN4=2, COOPER=3, BENTLEY=4; OPERATING=1, FIRMWARE=2,
BOOTLOADER=3). The corpus contradicts that: Gen3 = `0x40` would decode as
"BENTLEY", Ring 4/5 (`0x60`/`0x70`) as unknown hardware, and every ring as
mode 0 = "UNKNOWN". v1.1 reports `frame_type`, `generation_byte` /
`generation` and `fw_revision` instead.

### Service UUIDs

| UUID | Meaning | Routed? |
|---|---|---|
| `98ED0001-A541-11E4-B6A0-0002A5D5C51B` | Ring data service | yes |
| `8BC5888F-C577-4F5D-857F-377354093F13` | Charger puck | yes (`device_kind = charger_puck`) |
| `00060000-F8CE-11E4-ABF4-0002A5D5C51B` | **Cypress generic Bootloader (OTA) service** | **no** |

The Oura app scan-filters on the Cypress bootloader service to find rings in
DFU mode, but that UUID is Cypress/Infineon's stock bootloader service
(CySmart / PSoC Creator "Bootloader Service", AN97060) shared by any product
on a Cypress PSoC / CYW BLE part, so on its own it does not identify an Oura
ring.

## References

- [Cypress AN97060 — PSoC 4 BLE / PRoC BLE Over-the-Air (OTA) Device Firmware Upgrade](https://www.infineon.com/dgdl/Infineon-AN97060_PSoC_4_BLE_and_PRoC_BLE_-_Over-The-Air_(OTA)_Device_Firmware_Upgrade_(DFU)_Guide-ApplicationNotes-v09_00-EN.pdf) — Bootloader service `00060000-F8CE-11E4-ABF4-0002A5D5C51B`
- [Oura Ring product page](https://ouraring.com/)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
