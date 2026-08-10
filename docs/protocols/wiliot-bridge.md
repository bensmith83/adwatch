# Wiliot Bridge Relay Packet (`0xFCC6`)

## Overview

[Wiliot](https://www.wiliot.com/) builds **IoT Pixels** — battery-free BLE tags that harvest energy from ambient radio and broadcast an encrypted, per-packet-rotating payload. Pixels are too small and too power-starved to hold a connection, so a Wiliot deployment pairs them with **Bridges**: powered relay devices that hear pixel traffic and re-broadcast it toward a gateway, which forwards it to Wiliot's cloud where the payload is decrypted and resolved.

Wiliot holds three 16-bit SIG member UUIDs, and splits two of them by role:

| UUID | Registry owner | Role (per Wiliot's integration guide) |
|------|----------------|--------------------------------------|
| `0xFDAF` | Wiliot LTD | **Pixel** packets |
| `0xFCC6` | Wiliot LTD. | **Bridge** packets |
| `0xFC90` | Wiliot LTD. | (no published role) |

This document covers the `0xFCC6` **bridge** surface only.

Observed in the 2026-07-31 NearSight telemetry sweep: **109 records**, all under `0xFCC6`, all exactly **27 bytes**, all with no manufacturer data and no local name. Only **four** CoreBluetooth identifiers produced all 109 frames — consistent with a small number of stationary bridges relaying many pixels, rather than 109 separate devices.

## Supported Devices

| Device | Identification | Notes |
|--------|---------------|-------|
| Wiliot Bridge / gateway relay | Service data under `0xFCC6`, 27 bytes | Powered relay; re-broadcasts pixel traffic |
| Wiliot IoT Pixel | Service data under `0xFDAF` | **Not** covered by this parser |

Wiliot does not publish a model-level advertising distinction, so the parser identifies the *role*, not the SKU.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service data UUID | `0xFCC6` | SIG member UUID registered to Wiliot LTD. |
| Service-data length | exactly 27 bytes | 109/109 in capture; independently pinned by reelyActive's `advlib` as `DATA_LENGTH_BYTES = 27` |
| Manufacturer data | absent | 109/109 |
| Local name | absent | 109/109 |
| Address type | random | Rotates |

### Wire Layout

```
GG GG GG | 24-byte body
\___ ___/  \______________ ______________/
    \/                    \/
 3-byte group        opaque relayed payload
   prefix            (encrypted / cloud-resolved,
 (byte[1] == 0x00     different in EVERY packet)
  in 109/109)
```

### Group Prefixes Observed

| Prefix | Records |
|--------|---------|
| `bb003a` | 53 |
| `cf003a` | 29 |
| `0000ee` | 17 |
| `cf0039` | 4 |
| `030039` | 3 |
| `bb0039` | 3 |

Byte 0 takes four values (`bb`, `cf`, `00`, `03`), byte 1 is `0x00` in every single record, byte 2 takes three (`3a`, `39`, `ee`). Real samples:

```
bb003a 1232d8c86456d5ff9c67f8bc00a9822a012e2d59885ff8ae
cf003a 59e5efdd67f10993063bfec8001ca73056155a945e717375
0000ee 610dd956b159fbf30a01041e00000001041e000000000000
030039 345bb3c4eb6b389443bcfdb8007320bf049bcffa7cfbfa21
```

### Body Entropy

Per-byte value counts across all 109 records:

| Offset | Distinct values | Reading |
|--------|-----------------|---------|
| 0 | 4 | group prefix byte |
| 1 | **1** (`0x00`) | group prefix byte, constant |
| 2 | 3 | group prefix byte |
| 3–12 | 40–68 | high entropy |
| 13–14 | 23 each | mildly constrained |
| 15 | 9 (`0x00` in 95/109) | possibly a separator |
| 16–26 | 55–67 | high entropy |

Every one of the 109 bodies is distinct. That is the expected behaviour for a relay carrying a fresh encrypted pixel payload per packet — not a device broadcasting its own rotating state.

## Parser Scope (Passive Only)

The parser accepts a frame when the advertisement carries service data under `0xFCC6` of exactly 27 bytes, and reports:

- vendor (`Wiliot LTD.`) and the SIG UUID
- `packet_role = bridge`, with the Pixel/Bridge split recorded in metadata
- the 3-byte group prefix, plus `group_prefix_observed` (true for the six prefixes above, false otherwise)
- the 24-byte body, verbatim, flagged as intentionally undecoded

**It deliberately does not gate on the group prefix.** `0xFCC6` is a SIG-registered vendor allocation, so a 27-byte frame under it is a Wiliot frame regardless of group — an unrecognised prefix is surfaced as data rather than dropped, so a new Wiliot group shows up in the corpus instead of vanishing.

### What we cannot parse

The 24-byte body is encrypted and resolved server-side against a Wiliot account. This is not a gap in our analysis — the reference open-source implementation ([reelyActive `advlib-ble-services`](https://raw.githubusercontent.com/reelyactive/advlib-ble-services/master/lib/wiliot.js)) also relays the payload opaquely and makes no attempt to decode it. Pixel identity, sensor readings, and tag associations all live behind Wiliot's cloud API.

## Stable Identity

The body rotates every packet, so it cannot be an identity — keying on it would create one "device" per advertisement. Identity therefore keys on the BLE address, which is the only field stable across a bridge's consecutive advertisements:

```
identifierHash = sha256_16("wiliot_bridge:<mac>")
stableKey      = nil
```

Four identifiers across 109 frames in the capture supports this: bridges are stationary infrastructure, not privacy-rotating consumer devices.

## Detection Significance

- **Wiliot bridges mark an ambient-IoT deployment.** Seeing `0xFCC6` traffic means battery-free pixel tags are in use nearby — retail supply chain, pharma cold chain, or logistics asset tracking. The bridge is the visible half of an otherwise near-invisible tagging system.
- **High packet volume, low device count.** A handful of bridges can generate hundreds of distinct advertisement signatures in minutes. Anything counting distinct payloads as distinct devices will badly over-count a Wiliot site; keying on the address is required.
- **`0xFDAF` is the other half.** No `0xFDAF` pixel frames appeared in this corpus (the three `AFFD`/`FDAF` hex matches found were coincidental substrings inside unrelated Microsoft CDP and Tuya payloads). Worth watching for.

## References

- [Bluetooth SIG member UUIDs (canonical YAML)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — `0xFCC6`, `0xFDAF`, `0xFC90` all registered to Wiliot LTD.; verified locally 2026-07-31.
- [Wiliot integration guide](https://gist.github.com/vyshakhbabji/631b98dd78f769bbf8ad5db38c18a423) — *"Use 16b-UUID 0xFDAF to identify Wiliot Pixel packets or 16b-UUID 0xFCC6 to identify Wiliot Bridge packets."*
- [reelyActive `advlib-ble-services/lib/wiliot.js`](https://raw.githubusercontent.com/reelyactive/advlib-ble-services/master/lib/wiliot.js) — 27-byte length constant, opaque relay, no body decode.
- [Wiliot IoT Pixels product page](https://www.wiliot.com/product/iot-pixels) — battery-free tag background.
- `research/sweep-2026-07-31-candidates.md` (NearSight app repo) — cluster evidence, byte-frequency tables.
