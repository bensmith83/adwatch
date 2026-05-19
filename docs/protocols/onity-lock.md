# Onity / UTC Fire & Security BLE Lock Plugin

## Overview

The Bluetooth SIG company identifier `0x01F4` and the member service UUID `0xFEA7` are both registered to **UTC Fire and Security** — historically the parent of [Onity](https://www.onity.com/) (hotel locks), [LenelS2](https://buildings.honeywell.com/us/en/brands/our-brands/lenels2/security-products/blue-diamond) (BlueDiamond Mobile Ready Reader), Interlogix, Edwards, Kidde, and Chubb. The same Bluetooth identity (`0x01F4` / `FEA7`) is therefore used by several access-control products; the most commonly-encountered deployment is the **Onity HT / Trillium BLE / DirectKey** hotel-lock family, with **LenelS2 BlueDiamond Mobile Ready Reader** wall readers seen in enterprise installations.

The advertisement gives us:

1. A **stable 32-bit lock serial number** (matches the 7-digit decimal sticker the manufacturer prints on every unit).
2. A **hardware variant byte** that correlates 1:1 with the model/firmware suffix in the BLE local name.
3. A **status byte** whose semantics are not yet decoded (treated as opaque).

## Supported Devices

| Hardware variant byte | Model suffix in local name | Likely product |
|---|---|---|
| `0x90` | `0100108B` | Onity HT / Trillium DirectKey lock (most common) |
| `0x99` | `00008005` | Different model / generation in the same family |

Other variant bytes may appear and will still parse — the parser surfaces the raw variant byte and any suffix it can extract from the local name, then leaves model identification to downstream classification.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x01F4` | UTC Fire and Security (SIG-registered). |
| Service UUID | `0xFEA7` | UTC Fire and Security member UUID. |
| Local name | `^\d{8}\.[0-9A-Fa-f]{8}$` | `<serial>.<model/fw suffix>`, e.g. `"49124674.0100108B"`. |

The Bluetooth SIG company and member-UUID assignments are listed at the [SIG assigned-numbers index](https://www.bluetooth.com/specifications/assigned-numbers/) and mirrored at the [Bitbucket YAML source](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml).

### Manufacturer Data Layout (9 bytes)

```
Byte 0..1 : f4 01            — company ID 0x01F4 (LE)
Byte 2    : 0x01             — frame / protocol type (constant)
Byte 3    : 0x02             — product class (constant; high byte of full serial)
Byte 4..6 : SS SS SS         — low 24 bits of serial (big-endian)
Byte 7    : variant          — hardware variant (correlates with model suffix)
Byte 8    : status / flags   — value varies per unit; semantics unconfirmed
```

### Serial Decoding

The full 32-bit serial is `0x02_XX_YY_ZZ`, where `XX YY ZZ` are payload bytes 4..6 in big-endian order and the high byte `0x02` is fixed (it is the product-class byte at offset 3, reused as the serial's MSB).

| Payload bytes 4..6 | Serial (hex) | Serial (decimal) | Observed local name |
|---|---|---:|---|
| `ed 95 42` | `0x02ED9542` | 49,124,674 | `49124674.0100108B` |
| `ed 39 54` | `0x02ED3954` | 49,101,140 | `49101140.0100108B` |
| `ed 39 b5` | `0x02ED39B5` | 49,101,237 | `49101237.0100108B` |
| `ed 0a c9` | `0x02ED0AC9` | 49,089,225 | `49089225.00008005` |

The decimal serial is printed on every lock as a 7- or 8-digit sticker (model/serial label), so this number is what an installer or property manager will recognize when inventorying units.

### Local Name Format

`<8 decimal digits>.<8 hex digits>`

- Leading 8 digits = decimal serial (same value as bytes 4..6 + `0x02` MSB).
- Trailing 8 hex digits = model + firmware/HW revision suffix. We've observed `0100108B` (paired with variant byte `0x90`) and `00008005` (paired with variant byte `0x99`).

If the lock advertises without a `local_name` (some scans), the parser still decodes the serial — only the `model_suffix` field is then absent.

### Status Byte (unconfirmed)

Byte 8 of the manufacturer payload takes values like `0x00`, `0x04`, `0x7F`, `0xFF` and appears stable per unit across hours of sightings. We surface it raw as `status_byte` and leave its semantics as future work — likely candidates include battery / fault / open-state flags, but we have not validated.

## Detection Significance

- **Hotels, dorms, healthcare, multi-family residential.** A dense cluster of `0x01F4 / FEA7` advertisements is a strong signal that you're near an Onity-equipped property: hotel corridors typically expose hundreds of locks at once.
- **Stable plaintext serial enables surveillance.** Although CoreBluetooth rotates the BLE MAC, the 32-bit serial in bytes 4..6 (plus the duplicate serial in plaintext in the local name) is invariant per physical lock. A nearby scanner can enumerate every door in a building and re-identify each door across days.
- **Door inventory is trivial.** Walking a hallway with a BLE scanner returns a count of every Onity lock in earshot. For a property operator this is a useful asset-survey property; for a security-aware guest it is a real disclosure that the venue uses Onity gear.

## Privacy & Security Notes

- The serial is broadcast unauthenticated — anyone with a BLE radio can read it.
- The variant byte plus local-name suffix uniquely identify the model and firmware generation of every lock in earshot, which is useful information for an attacker comparing against published vulnerability research on specific Onity firmware revisions.
- The status byte is opaque to us; do not surface it as if it were decoded.

## What We Cannot Parse from Advertisements

- The lock-state (open / closed / armed) — likely not in the advertisement; would require a GATT connection and the manufacturer's app credentials.
- Mobile-key / pairing material — that traffic is GATT-side and authenticated.
- Battery level — almost certainly only readable via the manufacturer service.

## References

- [Onity HT / Trillium / DirectKey product overview](https://www.onity.com/en/us/)
- [LenelS2 BlueDiamond Mobile Ready Reader brochure (PDF)](https://www.lenel.com/assets/library/onguard/BlueDiamond%20Mobile%20Brochure.pdf)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
- [Bluetooth SIG member UUIDs (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml)
