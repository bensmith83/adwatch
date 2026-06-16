# Tuya BLE (Hangzhou Tuya Smart)

## Overview

Tuya (Hangzhou Tuya Smart Inc.) is the dominant Chinese white-label
IoT/smart-home platform — its firmware ships rebadged across hundreds of
brands (Fingerbots, smart locks, sensors, switches, breakers, appliances).
Tuya BLE devices advertise **service data under two 16-bit UUIDs** that map to
Tuya's two protocol generations. Observed in the 2026-06-15 NearSight sweep
(stationary smart-home gadgets, multi-day).

## Vendor attribution

**Hangzhou Tuya Smart Inc. — HIGH confidence**, on two independent anchors:

- **`0xFD50` is SIG-registered** to *"Hangzhou Tuya Information Technology Co.,
  Ltd"* in the SIG `member_uuids.yaml`. This is Tuya's **V2** service UUID.
- **`0xA201` is Tuya's V1** advertising/scan UUID — not SIG-allocated (a
  Tuya-chosen 16-bit value), but confirmed in **Tuya's own SDK**
  (`tuya/TuyaOpen`, `tal_bluetooth_def.h`:
  `TAL_BLE_SVC_SCAN_UUID_V1 = 0xA201`, `TAL_BLE_CMD_SERVICE_UUID_V2 = 0xFD50`)
  and used as the discovery key by the Home Assistant `ha_tuya_ble`
  integration (`service_data_uuid: 0000a201-…`).

So a device advertising under **0xFD50** is a newer-firmware (V2) Tuya device;
under **0xA201** is the legacy / most-common (V1) format.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Service UUID | `0xA201` (V1) and/or `0xFD50` (V2) |
| Manufacturer data | absent (typical) |
| Address type | random |

### Service data

| UUID | Version | SIG status | Sample payload |
|---|---|---|---|
| `0xA201` | V1 | not SIG-allocated (Tuya-chosen) | `00`, `002ebbe5d19a8c6f61a34f82e3b55dacff` |
| `0xFD50` | V2 | SIG → Hangzhou Tuya | `490000089bff3eaa79423029` |

The service-data payload is Tuya's framed/often-encrypted advertisement (the
first byte is a protocol/flags field). We surface it raw without claiming a
decode — the bytes do not carry a stable plaintext per-device ID, so the
rotating BLE address is the only key.

## Parser scope

Passive decode only. Surface `vendor`, `protocol_version` (v1/v2),
`advertising_uuid`, `sig_registered`, and `service_data_hex`. Prefers V2 when a
device somehow advertises both. Stable key falls back to the rotating MAC.

## Confidence

Vendor: **high** (SIG registration for FD50 + Tuya SDK source for A201). The
specific Tuya *product* behind any one advertisement is not determinable
passively (Tuya is a platform spanning thousands of SKUs).

## References

- BT SIG `member_uuids.yaml` — `0xFD50` = Hangzhou Tuya Information Technology.
- `tuya/TuyaOpen` `src/tal_bluetooth/include/tal_bluetooth_def.h` (A201/FD50).
- `pantherale0/ha_tuya_ble` `manifest.json` — 0xA201 discovery matcher.
- NearSight app: `Sources/Parsers/TuyaBLEParser.swift`.
