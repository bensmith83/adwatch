# Jieli ASCII Pseudo-CID HID Beacon ("ZHJIELI")

## Overview

Zhuhai Jieli Technology (珠海杰理) is one of the largest Bluetooth SoC
vendors; its chips sit in low-cost TWS earbuds, speakers, remote controls,
selfie shutters, toys and other peripherals under hundreds of brands. Its
Bluetooth SIG company ID is `0x05D6` — see [`jieli-audio.md`](./jieli-audio.md).

Some Jieli-firmware devices instead broadcast manufacturer data that is
nothing but the ASCII string **`ZHJIELI`** (ZHuhai JIELI). The first two
bytes, `5a 48` ("ZH"), are read by every BLE stack as a little-endian
company ID of `0x485A`, which is not SIG-assigned. The same self-label
appears elsewhere in the corpus as a local name (`ZHJIELI VM-207-BLE`,
2026-07-29 sweep).

First captured as a manufacturer-data frame in the 2026-08-25 telemetry
sweep: three units, 13 sightings over two days, every one advertising the
SIG HID service `0x1812` and no local name.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Pseudo company ID | `0x485A` (wire bytes `5a 48` = ASCII "ZH") | NOT SIG-assigned; Jieli's real slot is `0x05D6` |
| Manufacturer payload | exactly `4a 49 45 4c 49` = "JIELI" | Whole AD-0xFF field spells `ZHJIELI` |
| Service UUID | `0x1812` (HID over GATT) | Present on every capture; reported, not required |
| Local name | none | — |

### Manufacturer Data Layout

```
5a 48 | 4a 49 45 4c 49
"ZH"    "JIELI"
```

There are no fields: the frame is a 7-byte vendor self-label. Nothing in
it varies per unit — three units carried byte-identical payloads.

## Parser Scope (passive-only)

The parser accepts a frame only when the LE company ID is `0x485A` **and**
the payload is exactly `JIELI` (exact length, exact bytes — a longer
string that merely starts with `ZHJIELI` is left unclaimed, mirroring the
Bluetrum "Bl"/"Bluetrum" pseudo-CID parser). It reports:

| Field | Value |
|-------|-------|
| `ascii_string` | `ZHJIELI` |
| `company_id` | `0x485a` |
| `vendor` | Zhuhai Jieli Technology Co.,Ltd (chipset vendor, not the product brand) |
| `sig_id_status` / `sig_id_note` | `vanity_forged`; real SIG CID is `0x05D6` |
| `payload_hex` | `4a49454c49` |
| `hid_service_advertised` | `true` when `0x1812` is in the advertised UUID list |

Device class `peripheral`. Identity is **address-anchored** (no
`stableKey`): the payload is fleet-constant, so keying on it would merge
every unit into one device.

## Confidence and Attribution

- **Chipset vendor: HIGH.** The frame literally spells the vendor's name,
  and the same label is seen in Jieli-firmware local names.
- **Product: UNKNOWN.** Jieli silicon ships in many HID-class products
  (remotes, camera shutters, game pads, keyboards). The HID service says
  "input device", nothing more. Treat this as a chipset fingerprint, not a
  product attribution; a named capture (`ZHJIELI <model>`) would let the
  parser upgrade the label.

## References

- [Bluetooth SIG company identifiers](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — `0x05D6` = Zhuhai Jieli technology Co.,Ltd; `0x485A` absent
- [Jieli-Tech on GitHub](https://github.com/Jieli-Tech) — the vendor's SDKs (AC63xx / AW30N BLE, HID and remote-control targets)
- [`jieli-audio.md`](./jieli-audio.md) — the real-CID stream
- `docs/protocols/pseudo-cid-f0f0.md` and the Bluetrum ASCII pseudo-CID parser — sibling ASCII-in-CID exemplars
