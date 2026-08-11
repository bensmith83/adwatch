# Bouffalo Lab BLE Module (BL602 / BL604 / BL616 / BL702 SDK Default)

## Overview

**Bouffalo Lab (Nanjing) Co., Ltd.** is a Chinese fabless SoC vendor
whose BL602 / BL604 (BT 5.0 + Wi-Fi 4) and BL616 / BL702 (BT 5.2 /
5.3 + Wi-Fi 6) combo chips are widely OEM'd into Tuya-platform and
white-label smart-home accessories — plugs, bulbs, contact sensors,
thermometers, and so on. The Bouffalo BLE SDK ships with a default
local-name template of `TL-<chip-BD_ADDR>` (the literal string `TL-`
plus the 12-hex BD_ADDR with no separators); OEMs who don't customize
the firmware leak both the chipset family and the chip MAC in plain
sight.

This is a **chipset-family parser**, not a product-vendor parser — the
captured device is unbranded white-label hardware running stock SDK
firmware. The value is detecting the *category* of nearby unbranded
IoT-module presence rather than naming a specific product.

## Why a Strict OUI Gate

The literal prefix `TL-` collides with TP-Link's `TL-WAxxxRE` /
`TL-MR3020` router branding convention. TP-Link doesn't normally emit
BLE in this shape, but the prefix overlap is a real false-positive
risk. To avoid claiming any unrelated `TL-`-named device, the parser
requires the chip MAC's OUI to be in a small, IEEE-verified table of
Bouffalo Lab OUIs:

| OUI | Vendor | IEEE registration |
|---|---|---|
| `7C:B9:4C` | Bouffalo Lab (Nanjing) Co., Ltd. | MA-L, 2020-12-02 |

Add new OUIs only after IEEE confirmation. The parser will not match
`TL-<MAC12>` names whose MAC OUI is not in the table.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Local name | `TL-` + exactly 12 hex chars | `^TL-[0-9A-Fa-f]{12}$`; suffix is chip BD_ADDR |
| Chip MAC OUI | one of the Bouffalo OUIs above | must AND with name pattern |
| Manufacturer data | typically CID 0x0000 + tiny payload | NOT gated on — CID 0x0000 (Ericsson Tech Licensing) is a generic SDK default placeholder |
| Service UUIDs | *(typically absent)* | |
| Service data | *(typically absent)* | |
| Address type | `random` | |

### What We Can Surface

| Field | Source | Notes |
|---|---|---|
| Vendor | hard-coded | `Bouffalo Lab (Nanjing) Co., Ltd.` |
| `chipset_family` | hard-coded | `BL602/BL604/BL616/BL702` |
| `chip_mac` | localName | colon-formatted 6-octet MAC |
| `chip_oui` | localName | first 3 octets |
| `naming_convention` | hard-coded | `sdk_default_TL_macaddr` |

### What We Cannot Surface from the Advertisement

- Actual product brand / SKU (Tuya plug? Smart bulb? Generic sensor?).
- Live device state (on/off, current measurement, sensor reading).
- Pairing status, Wi-Fi configuration.
- Customer that OEM'd the chip (chip-buyer privacy).

All product-level state and identity requires a GATT connection plus
the Tuya / OEM-specific characteristic map (which varies per
buyer-of-the-chip — no universal protocol).

## Stable Identity

The chip MAC is the stable per-unit identifier — it's the chip's
BD_ADDR baked into firmware and survives the random-private-address
rotation the radio uses on-air:

```
stable_key = bouffalo_lab_ble_module:<chip_mac>
identifier = SHA256(stable_key)[:16]
```

## Detection Significance

- An unbranded Bouffalo-chipset BLE IoT device is in range. Most
  commonly a Tuya-ecosystem accessory (smart plug, bulb, sensor,
  thermostat) that didn't get a custom local-name configured at the
  factory.
- Useful for tallying generic-IoT presence at a site (vs branded
  Apple HomeKit / Google Home gear) without claiming false product
  attribution.
- The exposed chip MAC OUI is itself a useful forensic anchor —
  multiple captures from different MACs in the same OUI = multiple
  unrelated Bouffalo-chip devices, not one rotating.

## Adding a New OUI

1. Observe a recurring `TL-<MAC12>` capture across ≥2 exports whose OUI
   isn't in the current table.
2. Verify the OUI against the IEEE MA-L registry
   (`https://standards-oui.ieee.org/oui/oui.csv`) and confirm the
   assignee is Bouffalo Lab (parent or any subsidiary).
3. Add the OUI to the `bouffaloOUIs` set in
   `BouffaloLabBLEModuleParser.swift`.
4. Add a `@Test` case covering the new OUI.

## References

- [Bouffalo Lab product page](https://en.bouffalolab.com/product/)
- [Bouffalo Lab MAC vendor lookup (7C:B9:4C)](https://maclookup.app/vendors/bouffalo-lab-nanjing-co-ltd)
- [IEEE OUI registry CSV](https://standards-oui.ieee.org/oui/oui.csv)
- TechInsights teardown: [WUQI / Bouffalo BL602 floorplan](https://www.techinsights.com/blog/summary-wuqi-micro-wq7036ax-bt-53-le-audio-soc-floorplan-analysis) (related chipset family)
