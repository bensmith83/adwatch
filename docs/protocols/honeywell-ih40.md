# Honeywell IH40 UHF RFID Handheld Reader

## Overview

The **Honeywell IH40** (a.k.a. "SwiftRead Pro") is a pistol-grip
industrial UHF RFID + 1D/2D barcode handheld reader. It targets retail
and warehouse / T&L environments, with ~6 m UHF read range, BT 5.0,
and a field-replaceable battery. The IH40 typically docks/pairs with
Honeywell CT40/CT60/EDA51 mobile computers but can also operate
standalone, with a host phone or PC speaking BLE via the Honeywell
RFID SDK.

The BLE radio is on whenever the reader is powered; passive scanning
picks it up as a connectable, randomized-address beacon. The
advertisement is identification + presence only — live RFID tag reads,
battery state, and scanner status all live behind the GATT link.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0526` | Honeywell International Inc. (BT SIG) |
| Local name | `IH40` | Exact match; required for attribution |

Honeywell ships many other BLE products on the same SIG-assigned
company ID (Lyric thermostat, Home Pro doorbell, etc.), so attribution
gates on `localName == "IH40"` in addition to the CID.

## Wire Format

Captured frames are 3 or 4 bytes including the 2-byte CID:

```
26 05 | [class_byte] [state_byte?]
```

| Offset (post-cid) | Bytes | Field |
|-------------------|-------|-------|
| 0                 | varies | `class_byte` — `0x03` observed (inferred: RFID handheld) |
| 1                 | varies | `state_byte` — `0x03` observed (inferred: advertising / connectable); absent in short-form frames |

Both observed units broadcast `class_byte = 0x03` consistently;
`state_byte = 0x03` matches the "powered-on + BLE link available"
reading. The short-form 3-byte frame appears intermittently during the
inter-broadcast windows; the parser handles it gracefully.

## Captured Examples

```
IH40   mfr=26 05 03 03   (4-byte long form, 117 sightings)
IH40   mfr=26 05 03      (3-byte short form, 8 sightings)
```

Captured 2026-05-31 in `research/adwatch_export 14.json` — two distinct
units in the same site (retail / warehouse), ~125 sightings total.

## Identity Hashing

```
identifier_hash = SHA256("honeywell_ih40:mac:<MAC>")[:16]
```

The IH40 rotates its random address and exposes no serial in the
advertisement, so the only available stable identity is the current
BD_ADDR. Per-unit correlation across MAC rotations would require GATT.

## What We Cannot Parse Without GATT

- Live RFID tag read events
- Scanned barcode payloads
- Battery level
- Firmware version
- Trigger / scanner state (idle vs. scanning vs. paired)
- Serial / asset tag

All of those live behind the Honeywell RFID SDK GATT profile, not the
advertisement.

## References

- [Honeywell IH40 RFID Handheld Reader (product page)](https://sps.honeywell.com/us/en/products/productivity/rfid/readers/ih40-rfid-handheld-reader)
- [Honeywell IH40 datasheet PDF](https://prod-edam.honeywell.com/content/dam/honeywell-edam/sps/ppr/en-au/public/products/rfid/readers/ih40/documents/sps-ppr-ih40-rfid-reader-datasheet-en.pdf)
- [Honeywell IH40 Quick Start Guide PDF](https://prod-edam.honeywell.com/content/dam/honeywell-edam/sps/ppr/en-us/public/products/rfid/readers/ih40/documents/sps-ppr-ih40-rfid-en-qs.pdf)
- BT SIG company_identifiers.yaml: `0x0526 → Honeywell International Inc.`
