# General Motors PEPS (Passive Entry Passive Start) BLE Protocol

## Overview

General Motors vehicles with Passive Entry Passive Start advertise a BLE frame
under **service UUID `0xFE48`**, which is SIG-assigned to **General Motors**
(`member_uuids.yaml`; GM holds the `FE46`–`FE49` block). Some frames also carry
a self-identifying localName `GM_PEPS_VKS<n>` (PEPS = Passive Entry Passive
Start; `VKS` ≈ vehicle key slot).

Identified in the 2026-07-06 telemetry sweep. **Sourced from low-trust
(unattested) telemetry** — see the sweep write-up; the payload is a real
capture.

## Identification

| Signal | Value | Notes |
|---|---|---|
| Service UUID | `0xFE48` | **SIG-assigned to General Motors** — vendor-exclusive anchor |
| Local name | `GM_PEPS_VKS1` / `VKS3` / `VKS4` | present on some frames; ~half are name-null |
| Service data | 20-byte FE48 payload (below) | present on every frame |
| Address type | random | |
| Device class | `vehicle` | |

## FE48 service-data byte map (20 bytes)

Example: `01 0000 6bac506ed622fdc0 01 02 00000000000000`

| Offset | Bytes | Field | Behaviour |
|---|---|---|---|
| 0 | `01` | frame/format | constant |
| 1–2 | `00 00` | reserved | constant |
| **3–10** | **`6b ac 50 6e d6 22 fd c0`** | **8-byte vehicle id** | **constant across all captures AND across differing random MACs** |
| 11 | `01` / `03` / `04` | key-slot index | matches `VKS1` / `VKS3` / `VKS4` |
| 12 | `02` | state | constant |
| 13–19 | `00 × 7` | padding | constant |

The six observed records are one physical vehicle enumerating three key slots
(1/3/4); three of the six frames are name-null and are caught only by the FE48
service UUID.

## 🔒 Security / privacy finding

**The 8-byte vehicle id is broadcast in the clear and is stable across BLE MAC
randomization.** Any passive observer can therefore re-identify and track a
specific GM vehicle across time and location despite MAC rotation — the exact
class of privacy leak this tool exists to detect. The parser surfaces the id as
`vehicle_id_hex` and flags it via `privacy_note`, and uses it as the
MAC-rotation-proof stable key.

## Match rule

- **Primary:** service UUID `fe48` (present on every frame, incl. name-null).
- Gate in `parse()`: FE48 service-data present, `byte[0] == 0x01`, length 20.
- Secondary routing key: name `^GM_PEPS` (robustness; misses the name-null half).
- `stableKey = "gm_peps:" + vehicle_id_hex`.

Confidence: **VERY HIGH** (GM-exclusive SIG UUID + self-identifying name).
Only one vehicle observed, so per-vehicle uniqueness of the id field is inferred.

## References

- Bluetooth SIG `member_uuids.yaml` — `0xFE48` = General Motors (FE46–FE49 block).
- Parser: `GMPEPSParser` (`gm_peps`).
