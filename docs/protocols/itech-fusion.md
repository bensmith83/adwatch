# iTECH Wearables (AX Technologies) Fusion smartwatch

## Overview

**iTECH Fusion** (also marketed as iTOUCH Wearables) is a low-cost
consumer smartwatch family sold in the US through Walmart, Target, and
Amazon. The corporate entity behind iTECH/iTOUCH is **AX Technologies
LLC** (a.k.a. Axny Group / American Exchange Time LLC), 1400 Broadway,
18th Floor, New York, NY 10018 — the same address that holds the
**IEEE MA-L OUI `DC:71:DD`**, which the watch leaks into every BLE
advertisement.

The watch's BLE radio uses a random/RPA on-air address (so the
LL-layer MAC isn't a stable identifier), but the firmware emits the
**device's own BD_ADDR inside the manufacturer-data payload** —
giving us a stable per-unit identity even without connecting.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Manufacturer data | `59 00 DC 71 DD <NIC[3]>` (≥ 8 bytes) | CID 0x0059 (Nordic Semi) + AX Technologies OUI + 3-byte NIC tail |
| Local name | `iTECH Fusion <n>` exactly | `^iTECH Fusion \d+$` — e.g. `iTECH Fusion 3` |
| Service UUIDs | `["0001"]` | Non-standard vendor placeholder; informational, not gated |
| Address type | `random` | RPA / random-static; rotates |

**Either** the mfg structure **or** the strict name pattern is enough to
match — both signals appear together in fully-populated frames, but the
firmware also emits nameless variants where the mfg payload alone
identifies the device.

### CID 0x0059 caveat

`0x0059` is **Nordic Semiconductor ASA** — the chipset vendor, not iTECH.
Many Nordic-based products inherit this CID by default when the OEM
doesn't register their own. So CID 0x0059 alone is meaningless; the
decisive signal is the **AX Technologies OUI `DC:71:DD`** at bytes 2..4
of the manufacturer payload.

### Manufacturer-data layout (8-byte minimum)

| Bytes | Value | Meaning |
|---|---|---|
| 0..1 | `59 00` | CID 0x0059 (Nordic Semi) LE |
| 2..4 | `DC 71 DD` | AX Technologies OUI (IEEE MA-L) |
| 5..7 | `XX XX XX` | Per-device NIC tail (24-bit chip serial) |

The full BD_ADDR of the chip is `DC:71:DD:<NIC>` reconstructed.

### What we can surface

| Field | Source | Notes |
|---|---|---|
| `vendor` | hard-coded | `iTECH Wearables (AX Technologies)` |
| `chipset` | hard-coded | `Nordic Semiconductor (CID 0x0059)` |
| `oui` | hard-coded | `DC:71:DD` |
| `product` | localName | `iTECH Fusion <n>` if name present, else `iTECH Wearables device` |
| `model_number` | localName | `<n>` extracted from `iTECH Fusion <n>` |
| `device_nic` | mfg bytes 5..7 | colon-formatted `XX:XX:XX` |

### What we cannot surface

- Battery level, heart rate, step count, time, notifications — these
  require a GATT connection and the iTECH app's vendor-specific
  characteristic map.
- Pairing/connection state (not encoded in the observed advertisement).

## Stable identity

The 3-byte NIC tail is the per-unit stable identifier — it's the chip's
factory-baked BD_ADDR low half and survives the random-address rotation
the radio uses on-air:

```
stable_key = itech_fusion:<NIC>            (mfg present)
stable_key = itech_fusion:name:<full name> (mfg absent, name present)
identifier = SHA256(stable_key)[:16]
```

## Detection significance

- Identifies a low-cost smartwatch shipping millions of units in US
  big-box retail. Useful for benchmarking consumer wearable presence at
  a venue vs. the Apple Watch / Galaxy Watch / Fitbit baseline.
- The OUI gate prevents claiming unrelated Nordic-chipset devices —
  `DC:71:DD` is specifically AX Technologies' IEEE allocation.
- The strict `iTECH Fusion \d+` name regex avoids collision with the
  bare `iTECH` brand also used by unrelated computer accessories
  (mice, USB hubs, etc.).

## References

- [IEEE OUI registry CSV](https://standards-oui.ieee.org/oui/oui.csv) — `DC:71:DD` → AX Technologies, 1400 Broadway, NY
- [iTECH / iTOUCH Wearables at CES (Axny Group)](https://www.axnygroup.com/post/itouch-wearables-at-ces)
- [iTECH Fusion 3 product FAQ](https://support.itechwearables.com/en_us/itech-fusion-3-faqs-SkpuV87yA)
- [FCC grantee 2AS3P — American Exchange Time LLC smartwatch filing](https://fcc.report/FCC-ID/2AS3PITFRD21/5282415.pdf)
- [Bluetooth SIG company_identifiers.yaml](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — CID 0x0059 = Nordic Semiconductor ASA
- Captures: `research/nearsight_export 5.json` (16 sightings, 1 device, named + nameless variants).
