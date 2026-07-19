# Gree A/C — EWPE BLE+WiFi Module

## Overview

**Gree Electric Appliances** (Zhuhai, China — the world's largest
dedicated residential A/C manufacturer) ships many of its 2020+ split
systems with an integrated **WiFi+BLE control module** built by its
subsidiary **Zhuhai EWPE Information Technology Inc.** (OUI
`f4:91:1e`). The companion app is **EWPE Smart** (also branded
**GREE+**). The module advertises during pairing/provisioning and
continues to emit a short discovery frame post-pair so the EWPE Smart
app can find the unit on a new phone.

The BLE side has no SIG-registered company ID for Gree/EWPE; the module
firmware uses CID `0x005D` (IAR Systems' registered slot), which is a
common "left at SDK default" leakage rather than an intentional
attribution. As a result, **CID alone is not a usable signature**.

## Supported Models

| Product | Notes |
|---------|-------|
| Gree split A/C indoor unit | with GRJW05J6-class BLE+WiFi module |
| EWPE-rebranded OEM A/C | private-label units using the same module |

The parser identifies the module family, not specific A/C BTU
ratings or generations — those don't surface in the advertisement.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Manufacturer-data CID | `0x005D` | LE prefix `5D 00`; IAR Systems slot, squatted by EWPE |
| Mfg payload length | exactly 17 bytes | hard length gate |
| Mfg magic | `01 94 24 B8` at offset 4..7 | EWPE protocol marker — **decisive signal** |
| Mfg padding | `00 00 00 00 00 00` at offset 11..16 | constant trailing zeros |
| Local name | `GR-AC_<MID>_<HW>_<MAC4>(_SC)?` | optional; `_SC` suffix marks provisioned units |
| Service UUIDs | *(none in ad)* | |
| Address type | `random` | rotating private address |

### Local-Name Template

```
GR-AC_<MID>_<HW>_<MAC4>(_SC)?
        |     |    |       └─ "Smart Control" / provisioned-state suffix
        |     |    └────────── last 2 octets of BLE/WiFi-module MAC, lowercase hex
        |     └─────────────── hardware/protocol revision (02, 09 observed)
        └───────────────────── model/firmware family ID (10001, 10011 observed)
```

Observed concrete names:

- `GR-AC_10001_09_79cb_SC`
- `GR-AC_10001_09_929c_SC`
- `GR-AC_10011_02_d2d3` (from Home Assistant issue #67536 — un-provisioned variant)

### Manufacturer-Data Layout (17 bytes)

```
[0..1]   5D 00         CID 0x005D LE (squatted)
[2..3]   XX XX         state / pair-flag word (00 00 = un-paired, 00 02 = paired)
[4..7]   01 94 24 B8   EWPE protocol magic (CONSTANT)
[8]      XX            seq counter / partial MAC tail
[9..10]  XX XX         mac4 — matches 4-hex token in localName
[11..16] 00 00 00 00 00 00   reserved padding (CONSTANT zeros)
```

### Match Rule

Match if EITHER:

```
local_name matches /^GR-AC_\d+_\d+_[0-9a-f]{4}(_SC)?$/i
```

OR (the structural mfg test for nameless siblings):

```
mfg.count == 17
AND mfg[0..1] == 5D 00
AND mfg[4..7] == 01 94 24 B8
AND mfg[11..16] == 00 00 00 00 00 00
```

The 4-byte magic at offset 4..7 plus the 6-zero pad at offset 11..16
makes the false-positive rate near zero for the structural test.

### What We Can Parse

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Gree` |
| Product | hard-coded | `Air Conditioner (EWPE module)` |
| `model_id` | localName | when name present; `10001`, `10011`, … |
| `hw_rev` | localName | when name present; `02`, `09`, … |
| `mac4` | localName OR mfg[9..10] | stable per-module identifier |
| `paired` | localName `_SC` OR mfg state | `true` / `false` |

### What We Cannot Parse from the Advertisement

- Current set point / room temperature / mode (cool / heat / fan / dry).
- Power state (compressor running, fan speed).
- Filter / cleaning maintenance state.
- Wi-Fi connectivity to EWPE cloud.
- Energy consumption.

All live state requires the EWPE Smart cloud app or the JSON/UDP-7000
protocol that the unit speaks over Wi-Fi (see `tomikaa87/gree-remote`
and the openHAB `gree` binding).

## Stable Identity

`mac4` is the stable per-unit identifier — it's the last 2 octets of
the WiFi/BLE module's MAC and persists across BD_ADDR rotation. The
parser collapses named + nameless sibling frames from the same unit
on the same key:

```
stable_key = gree_ac:<mac4>
identifier = SHA256(stable_key)[:16]
```

## Detection Significance

- A Gree (or EWPE-rebranded) split A/C indoor unit is in range,
  presumably mains-powered and continuously broadcasting.
- The `paired` flag distinguishes units mid-setup from units already
  bound to an EWPE Smart account.
- The `model_id` field can hint at firmware generation when correlated
  across captures (10001 vs 10011 in our dataset).

## References

- [Home Assistant issue #67536 — GR-AC name + MAC correlation](https://github.com/home-assistant/core/issues/67536)
- [maclookup.app — OUI F4:91:1E = Zhuhai EWPE](https://maclookup.app/macaddress/F4911E)
- [GRJW05J6 WiFi+BLE module manual](https://manuals.plus/gree/grjw05j6-wifi-and-bluetooth-module-manual)
- [tomikaa87/gree-remote — reverse-engineered Wi-Fi app-layer protocol](https://github.com/tomikaa87/gree-remote)
- [bekmansurov/gree-hvac-protocol — UART-side Gree protocol notes](https://github.com/bekmansurov/gree-hvac-protocol)
- [openHAB Gree binding](https://www.openhab.org/addons/bindings/gree/)
- [EWPE Smart on the App Store](https://apps.apple.com/us/app/ewpe-smart/id1189467454)
- [FCC filing for a sibling Gree WiFi module (2ADAP-CS532Y)](https://fccid.io/2ADAP-CS532Y/User-Manual/User-Manual-2783760)
