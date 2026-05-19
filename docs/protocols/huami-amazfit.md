# Huami / Xiaomi / Amazfit / Zepp Wearables Plugin

## Overview

Bluetooth SIG company ID `0x0157` is registered to **Anhui Huami Information Technology Co., Ltd.** — the OEM behind Xiaomi's **Mi Band** line, the **Amazfit** brand (Cheetah, GTR, Bip, T-Rex), and the **Zepp** ecosystem. The same company ID covers products marketed under all three brands; the only way to tell them apart is the local name.

These wearables also advertise the SIG-allocated service UUID `0xFEE0` (Xiaomi/Huami private service).

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Company ID | `0x0157` (Huami) |
| Service UUID | `0xFEE0` |
| Local name | Marketing model (e.g. `"Mi Smart Band 5"`, `"Cheetah 2 Pro"`) |

### Manufacturer Data Layout (24 bytes after company ID)

```
Byte 0      : 0x02 — frame type
Bytes 1..16 : 0xFF × 16 — privacy-masked MAC slot (zeroed until paired)
Byte 17     : 0x03 — sub-frame tag
Bytes 18..23: 6 bytes — per-device identifier (the stable handle for the unit)
```

The 16 `0xFF` bytes are a Huami-specific privacy slot used during pairing: the device omits its public MAC there until the user explicitly confirms pairing in the Zepp app. The trailing 6 bytes are what we key on as the stable identifier — they survive resolvable-private-address rotation.

## Detection Significance

- **Fitness-tracker presence.** Mi Bands are among the most-shipped BLE wearables in the world; in a busy environment expect to see several. Amazfit watches are common in the running / outdoor crowd.
- **Stable 6-byte ID enables tracking.** Despite Apple's MAC rotation, the trailing identifier in the manufacturer payload persists across rotations and is broadcast unauthenticated.

## References

- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
- [Xiaomi Mi Smart Band 5 product page](https://www.mi.com/global/mi-smart-band-5/)
- [Amazfit Cheetah Pro](https://us.amazfit.com/products/amazfit-cheetah-pro)
