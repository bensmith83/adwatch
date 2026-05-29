# Honor (BLE Manufacturer-Data Frame)

## Overview

**Honor Device Co., Ltd.** is a smartphone and wearables maker spun out of Huawei in late 2020. Honor's BLE advertisement frames — captured in the wild from a phone-class device named `989822C687C3` (a MAC-address string with no separators) — use the manufacturer-data CID **`0x0211`**.

`0x0211` is *not* Honor's own SIG-allocated CID. Per the Bluetooth SIG company-identifier registry, `0x0211` belongs to **Telink Semiconductor Co., Ltd.**, the BLE chipset vendor whose silicon Honor ships in its phones and wearables. Honor's own CID is `0x09C6`, but the Telink BLE SDK populates the advertisement frame with the chipset vendor's CID and Honor has not overridden it. Several other Chinese OEMs (Xiaomi sub-brands in particular) exhibit the same pattern.

Because the CID alone is ambiguous (any Telink-chip device shares it), this parser locks onto the **frame shape** — specifically the doubled `11 22` TLV prefix and the nested `11 02 <token>` block — not the CID alone.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0211` | Telink Semiconductor (chipset vendor); Honor reuses it. Honor's own SIG CID is `0x09C6`, unused on the wire. |
| Local name | `<12 hex chars>` | Optional. MAC-address string with no separators, e.g. `989822C687C3`. Not the BLE advertiser's RPA. |
| Service UUIDs | none | |
| Address type | random | Resolvable Private Address, rotates per OS schedule. |

### Manufacturer Data Layout — short variant (8 bytes)

| Offset | Size | Field | Example |
|--------|------|-------|---------|
| 0..1 | 2 | Company ID (LE) | `11 02` (= `0x0211`) |
| 2..3 | 2 | TLV type / length prefix | `11 22` |
| 4..7 | 4 | Rotating token | `6d 51 f2 eb` |

### Manufacturer Data Layout — long variant (35 bytes)

| Offset | Size | Field | Example |
|--------|------|-------|---------|
| 0..1 | 2 | Company ID (LE) | `11 02` |
| 2..3 | 2 | TLV type / length prefix | `11 22` |
| 4..7 | 4 | Rotating token | `6d 51 f2 eb` |
| 8..9 | 2 | Nested CID echo | `11 02` |
| 10..13 | 4 | Nested rotating token (mirrors offset 4..7) | `6d 51 f2 eb` |
| 14 | 1 | Second TLV type | `25` |
| 15..18 | 4 | State-like quad (flips between `00 01 8b 00` / `00 01 99 00`) | `00 01 8b 00` |
| 19..23 | 5 | Constant token (unchanged across captures) | `78 6d eb f2 56` |
| 24 | 1 | Tail flag / counter | `1d` / `8f` |
| 25..34 | 10 | Telink SDK default-fill | `06 07 08 09 0a 0b 0c 0d 0e 0f` |

The trailing sequential run `06 07 ... 0f` is the Telink BLE SDK's default fill (analogous to Espressif and Nordic SDK leftovers). Its presence is a strong fingerprint of an un-customized Telink frame.

## Frame Variants

| Variant | Length | Notes |
|---------|--------|-------|
| Short | 8 bytes | Connectable / discovery-style frame; carries only the rotating token. |
| Long | 35 bytes | Pairing / extended-state frame; adds the nested token, state quad, constant token, tail flag, and SDK fill. |

Both variants were captured from the same physical device interleaved.

## What We Can Parse

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | CID + frame shape | `Honor` |
| `frame_size` | mfg length | `short` (8) or `long` (35) |
| `rotating_token_hex` | bytes 4..7 | Rotates per advertisement. |
| `nested_token_hex` | bytes 10..13 (long only) | Mirror of the rotating token. |
| `tail_flag_hex` | byte 24 (long only) | Single-byte counter / flag. |
| `payload_hex` | bytes 2..end | Full body after the CID. |
| `local_name_mac` | localName | When the MAC-style 12-hex name is present. |

## What We Cannot Parse

- Specific Honor model (phone vs. wearable, generation) — the frame carries no marketing string.
- Battery, pairing state, link key — out of scope for advertisement parsing.
- The semantic meaning of the state quad at bytes 15..18 (`00 01 8b 00` vs. `00 01 99 00`); appears to be a connection / pairing-mode toggle but unconfirmed.
- The 5-byte constant token at bytes 19..23 (`78 6d eb f2 56`); stable across all captures of this device, plausibly a salted device handle but unverified.
- Whether other Telink-chip devices (non-Honor) emit the same `11 22 ... 11 02` doubled-TLV shape — if so this parser will over-fire on them. We have not yet observed a non-Honor false positive.

## Detection Significance

- Identifies an Honor smartphone or wearable in the vicinity.
- The rotating token changes per ad, so it cannot be used for cross-session tracking; the BLE MAC rotates as an RPA at the OS interval, so we hash on the per-session MAC (`honor_ble:<mac>`) as the identifier.
- The MAC-style local name (`989822C687C3`) is a separate value from the RPA — likely a fixed device identifier the Honor BLE SDK exposes for in-ecosystem discovery (Honor Magic-Ring / Honor Share). It is not registered as an IEEE OUI and does not derive from the advertiser's RPA.

## References

- [Bluetooth SIG company identifiers (0x0211 = Telink Semiconductor; 0x09C6 = Honor Device Co., Ltd.)](https://www.bluetooth.com/specifications/assigned-numbers/company-identifiers/)
- [Nordic bluetooth-numbers-database (machine-readable mirror)](https://github.com/NordicSemiconductor/bluetooth-numbers-database)
- [Honor Device Co. background (Huawei spin-off, 2020)](https://www.hihonor.com/global/)
- [Telink Semiconductor BLE SDK overview](https://wiki.telink-semi.cn/wiki/Bluetooth-LE/)
