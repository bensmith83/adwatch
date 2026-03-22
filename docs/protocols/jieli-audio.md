# Jieli Audio Chipset BLE Protocol

## Overview

Zhuhai Jieli Technology manufactures BLE audio chipsets used by many budget audio brands including JLab, JBL (some models), and numerous white-label products. Devices broadcast using Jieli's company ID.

## Identifiers

- **Company ID:** `0x05D6` (Zhuhai Jieli Technology Co., Ltd.)
- **Local name patterns:** `JLab *`, `JBL *` (varies by OEM)
- **Device class:** `audio`, `speaker`, `headphones`

## Manufacturer Data Format

28 bytes observed (JLab):

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0-1 | 2 | Company ID | `0x05D6` (LE: `d605`) |
| 2 | 1 | Version? | `0x02` |
| 3-4 | 2 | Unknown | `0006` |
| 5-6 | 2 | Unknown | `0022` |
| 7-12 | 6 | Device address? | `3e5e525220a6` |
| 13-14 | 2 | Status | `0214` |
| 15-16 | 2 | Flags | `5000` |
| 17 | 1 | Unknown | `0b` |
| 18-19 | 2 | Unknown | `0102` |
| 20-27 | 8 | Padding | `00000000000000007f` |

## Sample Advertisements

```
JLab GO Pop+-App:
  Company ID: 0x05D6
  Manufacturer data: d60502000600223e5e525220a6021450000b010200000000000000007f
```

## OEM Brand Mapping

The Jieli chipset is used across many brands. Device identification relies on local_name rather than manufacturer data structure:

| Brand | Common Products |
|-------|----------------|
| JLab | GO Pop, GO Air, JBuds, Epic |
| Skullcandy | Some budget models |
| Anker Soundcore | Some models |
| Various | White-label BT speakers/earbuds |

## Parsing Strategy

1. Match on company_id `0x05D6`
2. Extract brand/model from local_name
3. Parse version byte at offset 2
4. Report device class based on name keywords (speaker, buds, headphones)

## Known Limitations

- Chipset-level company ID — many different OEMs
- Manufacturer data format may vary across Jieli chip generations
- No official protocol documentation from Jieli

## References

- Bluetooth SIG Company ID `0x05D6` — Zhuhai Jieli Technology
- Jieli AC695x/AC696x BLE audio SoC datasheets (not publicly available)
