# "OPEN"-marker proprietary BLE mesh (AP2 / RP roles)

## Overview

A multi-node BLE mesh observed in the 2026-06-15 NearSight telemetry sweep:
**22 distinct devices**, ~6,400 sightings, 2026-06-09…06-14, all in one
residential environment, all sharing a single 6-byte network ID. Two device
roles advertise the same proprietary manufacturer-data frame whose
load-bearing feature is the ASCII marker **"OPEN"**:

| Role | Local-name shape | Company ID | mfg length |
|---|---|---|---|
| Repeater | `RP-<12 hex>` (e.g. `RP-F47E8E4A2EED`) | `0x0131` (Cypress Semiconductor) | 26 bytes |
| Access point gen 2 | `AP2-<12 hex>-<fw>` (e.g. `AP2-C0005B33AC52-12070002`) | `0x0059` (Nordic Semiconductor) | 24 bytes |

The two roles share one network and clearly belong to one product family
(identical frame, shared installation ID, complementary role codes). The
silicon split — Cypress for repeaters, Nordic for access points — most
plausibly reflects two hardware suppliers/generations within one ecosystem.

## Vendor attribution

**Not attributed.** Both company IDs are **silicon-vendor factory defaults**
(Cypress `0x0131`, Nordic `0x0059`), i.e. the maker never registered its own
Bluetooth SIG company ID — device identity lives entirely in the proprietary
"OPEN" payload. Multi-source web research (2026-06) ruled out the obvious
multi-node candidates:

- **Itron OpenWay / OpenWay Riva AMI** — RULED OUT. Itron's network is
  sub-GHz RF mesh (902–928 MHz), not BLE; its only BLE is the transient
  handheld Itron Mobile Radio, which advertises `IMRnnnnnn`. Itron's role
  vocabulary is "Cell Relay / Router / Routing Node / Range Extender", never
  `AP2`/`RP`. The `OPEN` marker is not "OpenWay" in any Itron document.
- **Amazon Sidewalk** — RULED OUT (AMA service UUID + company ID 0x0171,
  defined frame; no ASCII `OPEN`, no `AP2-`/`RP-` names).
- **Consumer Wi-Fi mesh pods** (Xfinity/Plume, eero, Nest Wifi, Deco, Orbi) —
  RULED OUT (BLE only transient during onboarding, not a standing
  clock-broadcasting fleet).
- **Hunter Douglas PowerView Gen 3** — best *behavioural* fit (BLE
  repeater+gateway roles, ~30 nodes/home) but RULED OUT by signature: company
  ID 0x0819, service UUID `CAFE1001-…`, local name "PowerView Shade".

The marker "OPEN" is **not** the Wi-Fi access-point vendor "Open-Mesh" /
Datto — that is an unrelated 802.11 product line. The 12-hex IDs embedded in
the local names are **not** registered IEEE OUIs (checked against the IEEE
registry), so they are internal device IDs, not MACs. The `12070002`-style
AP2 suffix is a stable firmware/hardware version tag.

When a labelled specimen turns up (a companion app, a GATT service capture, or
a vendor decal), the `vendor` metadata is the place to upgrade.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Company ID | `0x0131` (RP) or `0x0059` (AP2) |
| Magic marker | ASCII `"OPEN"` (`4f 50 45 4e`) at manufacturer-payload offset 7 |
| Local name | `RP-<12hex>` or `AP2-<12hex>-<fw>` |
| Address type | random |

Match gate: company ID ∈ {0x0131, 0x0059} **AND** "OPEN" at payload offset 7.
That gate is tight enough to coexist with the other parsers that share these
chip CIDs (e.g. iTECH Fusion on Nordic 0x0059) without false positives.

### Byte map (offsets AFTER the 2-byte company ID)

```
RP  31 01 | 9730cf43ea36 | 00 | 4f50454e | 51 | 00 | 6a2dae22 | 0a 00000001 0000
AP2 59 00 | 9730cf43ea36 | 00 | 4f50454e | 8a | 00 | 6a2daee5 | 00000000 01
           \__network ID_/  \_  "OPEN"  _/ role  fl  \_clock_/  \_ trailing _/
off:        0..5            6   7..10     11   12   13..16       17..
```

| Offset | Field | Notes |
|---|---|---|
| 0..5 | network/installation ID | 6 bytes, **constant** across all 22 nodes (`9730cf43ea36`) |
| 6 | separator | `0x00` |
| 7..10 | `"OPEN"` marker | `4f 50 45 4e` |
| 11 | role code | `0x51` = RP/repeater, `0x8a` = AP2/access point |
| 12 | sub-flag | `0x00` on RP; `0x00`/`0x17`/`0x18` on AP2 |
| 13..16 | device wall clock | **big-endian uint32 Unix epoch** |
| 17.. | trailing constants | role-dependent (`0a 00000001 0000` / `00000000 01`) |

### Device clock — verified

The uint32 at offset 13..16 is the emitting device's clock, **verified to the
second** against capture time:

| Frame | Decoded | Capture (`lastSeen`) |
|---|---|---|
| `6a2dae22` (RP) | 2026-06-13T19:23:14Z | 2026-06-13T19:27:10Z |
| `6a2daee5` (AP2) | 2026-06-13T19:26:29Z | 2026-06-13T19:26:30Z |
| `6a2eaecd` (RP, next day) | 2026-06-14T13:38:21Z | 2026-06-14T13:45:54Z |

## Parser scope

Passive advertisement decode only. We surface: `network_id`, `role` +
`role_code`, `chip_company_id`, `device_clock_epoch` / `device_clock_utc`,
`device_name`, and `ap_firmware` (AP2). Stable key is
`open_marker_mesh:<network_id>:<device-id-from-name-or-MAC>` — the
name-embedded device ID survives BLE random-address rotation. No GATT
interaction; no vendor claimed.

## Confidence

- Decode (network ID, role, device clock): **high** (cross-validated across
  both roles and multiple days; 340 records replay cleanly).
- Vendor attribution: **none** — shipped as an honest descriptive family.

## References

- NearSight app: `Sources/Parsers/OpenMarkerMeshParser.swift`,
  `research/sweep-2026-06-15-candidates.md`.
- BT SIG `company_identifiers.yaml` (0x0131 Cypress, 0x0059 Nordic).
- IEEE OUI registry (name-embedded 12-hex IDs absent → not real OUIs).
