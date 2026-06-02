# Specifi-Kali Motion Sensor (`MOTION_xxxx`)

## Overview

A BLE PIR motion sensor advertising as `MOTION_<4 hex>` (e.g. `MOTION_0476`,
`MOTION_FD0A`, `MOTION_F5C7`). Manufacturer ID `0x0502` is registered by the
Bluetooth SIG to **Specifi-Kali LLC**, a small Austin, TX hardware company
better known for the Laelaps GPS dog-tracking collar system (FCC ID `2AFKF`).
The `MOTION` family appears to be a newer or undocumented Specifi-Kali
product line — or an OEM build using their assigned CID.

## Manufacturer

**Specifi-Kali LLC** — Austin, Texas. Public catalog: Laelaps GPS dog
tracker (collar + pointer). The `MOTION_xxxx` family is unconfirmed in
their public product listings, but the CID assignment is verified against
the SIG yaml.

## BLE Advertisement Structure

### Manufacturer Data

| Offset (post-CID) | Length | Field | Notes |
|-------------------|--------|-------|-------|
| 0 | 2 | reserved (`0x00 0x00`) | constant across observed captures |
| 2 | 4 | unit serial | per-unit identifier (likely 4 lower bytes of a hardware MAC or a manufacturer serial) |
| 6 | 2 | `unit_id` | 16-bit value identical to the hex suffix of the `MOTION_xxxx` local name |

Total payload length (excluding the 2-byte CID): **10 bytes**.

### Examples

| Local name | Mfr payload (post-CID) | unit_id | serial |
|------------|------------------------|---------|--------|
| `MOTION_0476` | `00 00 4A 47 7F 54 04 76` | `0476` | `4a477f54` |
| `MOTION_FD0A` | `00 00 4A 47 60 8F FD 0A` | `fd0a` | `4a47608f` |
| `MOTION_F5C7` | `00 00 7B 98 8F BB F5 C7` | `f5c7` | `7b988fbb` |

Note: units `0476` and `FD0A` share the leading serial bytes `4A 47`,
suggesting a manufacturing batch or model marker (`4A 47` = ASCII `"JG"`).
Unit `F5C7` carries a different leading pair (`7B 98`), so the prefix is
not a fixed model field — at most a batch identifier.

### Local Name

```
MOTION_<4 hex>
```

The 4 hex digits **must match the trailing two bytes of the manufacturer
payload**. The parser enforces that alignment so it doesn't false-positive
on incidental `0x0502` broadcasts from other Specifi-Kali products.

### Advertisement Behavior

- No service UUIDs, no service data — only manufacturer data + local name.
- 10-byte payload fits within the legacy 31-byte advertising limit; no
  extended-advertising hardware required.
- The advertisement carries identity only — there is no motion-event bit,
  battery byte, or RSSI-encoded distance. Motion events are presumably
  delivered via GATT after pairing.

## Identification

- **Primary**: CID `0x0502` **and** the 10-byte payload skeleton with the
  trailing 2 bytes matching the `MOTION_xxxx` name suffix.
- **Secondary**: local name regex `^MOTION_[0-9A-Fa-f]{4}$`.
- **Device class**: `motion_sensor`.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | CID `0x0502` | Specifi-Kali LLC |
| Unit ID | mfr bytes 6–7 / local-name suffix | stable 16-bit identifier |
| Unit serial | mfr bytes 2–5 | stable per-unit, can be used to fold MAC rotations |

## What We Cannot Parse (requires GATT)

- Motion-event state (active / idle)
- Battery level
- Firmware version
- PIR sensitivity / configuration

## Stable Identity

Identity is anchored on `unit_id` (the 4-hex suffix), **not** the BLE MAC.
Since CoreBluetooth rotates BLE MACs, the parser uses
`stable_key = specifi_kali_motion:<unit_id>` so multiple "different MAC"
sightings of the same physical sensor fold back into one device.

## References

- Bluetooth SIG company_identifiers.yaml (`0x0502 → Specifi-Kali LLC`) —
  <https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml>
- Specifi-Kali LLC D&B profile —
  <https://www.dnb.com/business-directory/company-profiles.specifi-kali_llc.467b39572617c3ff342fed3140678831.html>
- Laelaps GPS Dog Tracker (Specifi-Kali's public product) —
  <https://laelapsgps.com/dog-tracker/>
- FCC ID listings for Specifi-Kali (`2AFKF`) — <https://fccid.io/2AFKF>
