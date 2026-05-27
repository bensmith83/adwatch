# COROS GPS Sport Watches Plugin

## Overview

[COROS Wearables](https://coros.com/) is a GPS-enabled multisport watch maker (PACE 2/3, APEX 2 / 2 Pro, VERTIX 2 / 2S). The watch advertises continuously over BLE so the COROS app can re-pair without user intervention. COROS reuses **Tencent's BLE SDK**, which surfaces a recognizable signal mix: the Tencent SIG member-service UUID `0xFEE7`, a proprietary 16-bit service `0x3802` with a 6-byte service-data payload, plus the standard Battery (`0x180F`) and Device Information (`0x180A`) services.

This parser pulls the watch family (PACE 3 / APEX 2 / VERTIX 2 / …) and the per-unit MAC suffix out of the local name, surfaces the proprietary `0x3802` service-data payload for further inspection, and uses the MAC suffix as the stable key so MAC rotations collapse to a single device.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Local name | `^COROS .+ [0-9A-Fa-f]{6}$` | E.g. `"COROS PACE 3 805FB7"`. The 6-hex suffix is the last three bytes of the BD_ADDR — same value across consecutive ads of the same physical watch. |
| Service UUID | `0xFEE7` | Tencent Holdings Limited (SIG member services). Reused by COROS because they ship Tencent's BLE SDK. **Not** COROS-exclusive — Tencent SDK appears in many Chinese-vendor wearables — so we only rank-rather-than-gate on this UUID. |
| Service UUID | `0x3802` (custom) | Not in any SIG range; COROS/Tencent-SDK specific. The 6-byte service-data payload is exposed in metadata as `service_data_3802`. |
| Service UUID | `0x180F`, `0x180A` | Standard Battery + Device Information. |
| Company ID / mfg data | _absent_ | COROS does not advertise manufacturer-specific data. |

### Local Name Format

`COROS <FAMILY> <MODEL> <6-hex MAC suffix>`

Example: `"COROS PACE 3 805FB7"` → model `PACE 3`, MAC suffix `805FB7`.

The regex captures any model token between the `COROS ` prefix and the trailing 6-hex suffix, so newer products following the same scheme (`COROS APEX 3`, `COROS VERTIX 3`, …) parse without code changes.

### Service Data 0x3802

6 bytes per advertisement (e.g. `f7 af 1d 2c 03 90`). The payload is **not** the same as the MAC suffix in the local name. Most likely a device or firmware identifier / pairing token / per-session TLV consumed by the COROS app for fast device recognition during scan. Surfaced as `service_data_3802` in metadata for inspection.

## Detection Significance

- **Stable per-device.** The 6-hex MAC suffix in the local name is the same value across every advertisement from a given watch (until the underlying random BD_ADDR is rotated by the controller, which on a sport watch is rare in practice).
- **Cluster of FEE7.** Multiple `0xFEE7` advertisers at once — especially mixed with the COROS prefix — is a strong "running event / triathlon transition area" indicator.

## What We Cannot Parse from Advertisements

- Workout state (recording / paused / GPS lock / heart-rate sensor connection) — almost certainly only available over the GATT connection that the COROS app establishes via a Nordic-UART-style command service.
- Real-time HR / cadence / power — these are negotiated post-connect.
- Firmware version — exposed by the `0x180A` Device Information service post-connect, not in the advertisement.

## References

- [COROS product line](https://coros.com/)
- [SySS BLE analysis of COROS PACE 3](https://blog.syss.com/posts/bluetooth-analysis-coros-pace-3/) — confirms local-name suffix = last 3 bytes of BD_ADDR.
- [SySS COROS firmware analysis](https://blog.syss.com/posts/coros-firmware-analysis/)
- [Gadgetbridge issue #3929 (PACE 3)](https://codeberg.org/Freeyourgadget/Gadgetbridge/issues/3929)
- [bleak UUID table (0xFEE7 → Tencent Holdings Limited)](https://bleak.readthedocs.io/en/latest/_modules/bleak/uuids.html)
- [Bluetooth SIG member UUIDs (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml)
