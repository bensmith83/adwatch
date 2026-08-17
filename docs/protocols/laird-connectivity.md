# Laird Connectivity / Ezurio BLE module family (CID 0x0077)

## Overview

**Laird Connectivity LLC** (rebranded to **Ezurio** in March 2024) is a
US-based BLE module and sensor vendor whose **Sentrius** sensor line and
**BL653 / BL654 / BL5340** combo modules are widely OEM'd into industrial
and enterprise IoT products. Their Bluetooth SIG company identifier is
**`0x0077`** — currently registered as "Laird Connectivity LLC" in
canonical `company_identifiers.yaml`.

The captured device under this signature broadcasts a custom local name
(`ENS`) and a 43-byte mfg payload whose byte layout does **not** match
the documented Sentrius BT510 / BT610 LE-Coded-PHY frame structure
(reelyactive `advlib-ble-manufacturers/lairdconnectivity.js`). The most
likely interpretation: a **Laird-module-based OEM product** where the
integrator configured a custom name and a custom payload format.

This is a **chipset-family parser**, not a product parser — we surface
vendor attribution at the module-family level and avoid claiming any
specific SKU (BT510, BT610, BT710, etc.) without further evidence.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Company ID | `0x0077` | BT SIG → Laird Connectivity LLC (Ezurio) |
| Mfg total length | 45 bytes (CID + 43-byte payload) | The OEM-firmware shape we've observed |
| Local name | custom (e.g. `ENS`) | Integrator-chosen — not a documented Laird default |
| Service UUIDs | *(typically absent)* | |
| Address type | `random` (LL layer) | But the on-payload BD_ADDR is static-random |

### Manufacturer-data layout (45 bytes total)

| Bytes | Value | Meaning |
|---|---|---|
| 0..1 | `77 00` | CID 0x0077 LE (Laird/Ezurio) |
| 2..7 | `XX XX XX XX XX XX` | Device BD_ADDR (static-random — top 2 bits of byte 2 == 0b11) |
| 8..19 | 12 × `00` | Reserved / unpopulated sensor channels |
| 20 | `XX` | Sequence counter / record number |
| 21..32 | 12 × `00` | Reserved / unpopulated payload slots |
| 33..44 | 12 bytes | Event tail (likely opaque integrity tag / MIC / fingerprint) |

### Why the strict 45-byte gate

The 43-byte payload-after-CID layout (BD_ADDR + dual zero blocks + counter
+ tail) is distinctive enough to anchor attribution. CID 0x0077 alone is
not safe to gate on — vendor CIDs occasionally see unrelated devices reuse
them, and the length+structure gate avoids over-fire on any future Laird
device with a different frame.

### What we surface

| Field | Source | Notes |
|---|---|---|
| `vendor` | hard-coded | `Laird Connectivity LLC (Ezurio)` |
| `company_id` | hard-coded | `0x0077` |
| `chipset_family` | hard-coded | `Laird Sentrius / BL653 / BL654 / BL5340` |
| `device_bd_addr` | mfg bytes 2..7 | colon-formatted MAC |
| `address_kind` | mfg byte 2 high bits | `random_static` / `public` / `random_resolvable_private` / `random_non_resolvable` |
| `sequence_counter` | mfg byte 20 | decimal integer |
| `device_name` | localName | custom integrator label (`ENS` in our capture) |

### What we cannot surface

- Specific SKU (BT510 / BT610 / BT710 / custom OEM product).
- Sensor channel values — the zero-padded blocks in the captured frame
  suggest the device is idle or that this firmware doesn't populate the
  documented Sentrius sensor fields.
- Pairing / provisioning state.
- Meaning of the 12-byte event tail.

## Stable identity

The BD_ADDR encoded in the payload (mfg bytes 2..7) is the per-unit
stable identifier — it survives the BLE-layer random-address rotation
because it's encoded as a payload field rather than the LL header.

```
stable_key = laird_connectivity:<BD_ADDR>
identifier = SHA256(stable_key)[:16]
```

## Detection significance

- Identifies a Laird/Ezurio-module-based BLE device in range. Useful at
  industrial / commercial venues where Laird's Sentrius sensor family or
  BL65x modules are commonly deployed.
- Conservative attribution: we don't claim a specific SKU, only the
  vendor and module-chipset family.
- The 45-byte mfg-length gate keeps the parser from over-firing on the
  documented Sentrius BT510 / BT610 LE-Coded-PHY frames (different length
  and structure), so adding a real Sentrius parser later won't conflict.

## Future work

- If more captures surface across multiple devices, decode the 12-byte
  event tail and the role of byte 20 (sequence vs. record type) more
  precisely.
- If a Sentrius BT510 / BT610 frame ever appears in captures, write a
  separate, dedicated Sentrius parser with the documented layout
  (protocol/network/flags at offsets 2..5 etc.) and keep this parser as
  the catch-all for non-Sentrius Laird-module devices.

## References

- [Bluetooth SIG company_identifiers.yaml](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — `0x0077` = Laird Connectivity LLC.
- [Ezurio rebrand announcement (March 2024)](https://www.ezurio.com/) — successor entity.
- [reelyactive advlib lairdconnectivity.js](https://github.com/reelyactive/advlib-ble-manufacturers) — Sentrius BT610 1M-PHY reference layout (which our capture does NOT match).
- [Laird Sentrius BT510 manual (LE-Coded-PHY format)](https://www.manualslib.com/manual/2600786/Laird-Sentrius-Bt610.html?page=15) — alternative documented Laird frame.
- Captures: `research/nearsight_export 5.json` (106 sightings, 1 device, custom localName "ENS").
