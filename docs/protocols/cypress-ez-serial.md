# Cypress / Infineon EZ-Serial OEM Modules

## Overview

Cypress Semiconductor (acquired by Infineon in 2020) ships the
**EZ-Serial / EZ-BLE** firmware platform as the default GATT profile
on its CYBLE-xxx PSoC-4-BLE PRoC modules. EZ-Serial is a UART-over-BLE
profile that lets an OEM integrator drop a Cypress BLE module into a
product, talk to it via AT commands, and immediately get a working
BLE peripheral with no firmware development.

When the integrator never customizes the firmware, the resulting
product advertises the **stock EZ-Serial service UUID** with no
localName and a mostly-zero manufacturer-data block. Recognising that
signature lets us flag the device as an unattributed Cypress EZ-Serial
module instead of leaving it completely unparsed.

The captured devices were two distinct nameless units broadcasting the
stock UUID with the default-zero or BD_ADDR-derived manufacturer-data
slot. Likely host products: cheap dongle, vape, scale, novelty toy, or
in-store demo PCB.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0131` | Cypress Semiconductor Corporation (BT SIG) |
| Service UUID family | `65333333-A115-11E2-9E9A-0800200CA10X` | EZ-Serial; suffix `X` selects characteristic (0 = service, 2 = unacknowledged-data notify) |
| Local name | (absent) | A real customized product would set one |

The UUID family is a hand-tweak of the Java `UUID` javadoc example
UUID `…0800200C9A66` (note the `9A66` → `CA100` bump) with a v1
timestamp from early 2012. The parser matches any hex suffix in the
family (0–F) so characteristic-UUID-only ads still match.

## Wire Format

Two manufacturer-data variants captured:

```
mfg = 31 01 [00 00 00 00 00]            — 5 bytes of zeros (default uninitialized slot)
mfg = 31 01 [cd 56 57 ab]               — 4-byte EZ-Serial id (BD_ADDR-low bytes)
```

| Offset (post-cid) | Bytes | Field |
|-------------------|-------|-------|
| 0–3               | 4     | `ezserial_id_hex` (when non-zero) — lower 4 octets of the module's public BD_ADDR; surfaced as the per-module identity |
| 0–4               | 5     | all-zero slot — uninitialized; parser skips it |

The `ezserial_id_hex` is what the EZ-Serial firmware writes into the
manufacturer-data slot when no friendly name is configured; in
practice it is the low 4 octets of the module's BD_ADDR.

## Captured Examples

```
mfg = 31 01 00 00 00 00 00              (13 sightings — uninitialized)
mfg = 31 01 cd 56 57 ab                 (4 sightings — id slot populated)
```

Captured 2026-05-31 in `research/adwatch_export 14.json` — two distinct
units, ~17 sightings total.

## Identity Hashing

```
identifier_hash = SHA256("cypress_ez_serial:id:<ezserial_id_hex>")[:16]   # when id present
identifier_hash = SHA256("cypress_ez_serial:mac:<MAC>")[:16]              # fallback
```

When the `ezserial_id_hex` slot is populated, it's stable across MAC
rotations (it's derived from the public BD_ADDR, which doesn't rotate),
so it serves as the per-module identity. The all-zero variant falls
back to the rotating BD_ADDR.

## What We Cannot Parse Without GATT

- The OEM product the module is embedded in
- Whatever the integrator is pushing over the EZ-Serial UART pipe
  (sensor data, control commands, scale readings, etc.)
- Battery level (host-MCU-dependent)
- Module firmware version

EZ-Serial deliberately keeps the BLE radio layer dumb so the host MCU
can drive whatever protocol it wants over the GATT UART pipe. Without
GATT we can't see any of that.

## References

- [Cypress PSoC-4-BLE forum — `65333333-A115-11E2-9E9A-0800200CA102` documented as EZ-Serial unacknowledged-data characteristic](https://cypress703.rssing.com/chan-69235443/all_p21.html)
- [Cypress / Infineon AIROC EZ-Serial / EZ-BLE Module Firmware Platform](https://www.cypress.com/documentation/software-and-drivers/ez-serial-ez-ble-module-firmware-platform)
- BT SIG company_identifiers.yaml: `0x0131 → Cypress Semiconductor Corporation`
