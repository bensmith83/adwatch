# iHealth / Andon BP5S Blood Pressure Monitor

## Overview

The BP5S is a Bluetooth-enabled arm blood pressure monitor made by iHealth (a subsidiary of Andon Health Co., Ltd., Tianjin, China). It syncs measurements to the iHealth MyVitals app via BLE. The BLE advertisement serves as a discovery beacon for the app — no blood pressure readings are exposed in the advertisement.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `BP5S XXXXX` | 5-digit serial number suffix |
| Service UUID | `636F6D2E-6A69-7561-6E2E-425056323500` | 128-bit custom UUID (ASCII: `com.jiuan.BPV25\0`) |
| Company ID | `0x0059` (decimal 89) | Andon Health Co., Ltd. |

### Manufacturer Data

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0-1 | 2 bytes | Company ID | `0x0059` — Andon Health Co., Ltd. (LE: `5900`) |
| 2-11 | 10 bytes | Payload | `00000000004d323c1b68` — largely static, purpose unknown |

### Service UUID Decode

The 128-bit UUID decodes as ASCII text:
```
63 6F 6D 2E = "com."
6A 69 75 61 = "jiua"
6E 2E 42 50 = "n.BP"
56 32 35 00 = "V25\0"
```
Full string: `com.jiuan.BPV25` — this is the Jiuan (iHealth parent company) Bluetooth protocol identifier for BP V2.5.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid or local_name | BP5S monitor nearby |
| Serial number | local_name suffix | e.g. `11070` from `BP5S 11070` |
| Manufacturer | company_id `0x0059` | Andon Health / iHealth |

### What We Cannot Parse (requires GATT)

- Blood pressure readings (systolic, diastolic, pulse)
- Measurement history
- Device battery level
- User profiles
- Irregular heartbeat detection results

## Device Class

```
blood_pressure_monitor
```

## Known Protocol Details

- iHealth uses a custom GATT protocol under the `com.jiuan` namespace
- The iHealth SDK (deprecated) previously documented some BLE characteristics
- Communication requires pairing with the iHealth MyVitals app
- Measurements are stored on-device and synced in batch over BLE

## Open Source References

- [iHealth Open API](https://developer.ihealthlabs.com/) — deprecated developer portal (was used for cloud API access)
- [Bluetooth SIG Company ID 0x0059](https://www.bluetooth.com/specifications/assigned-numbers/) — Andon Health Co., Ltd.
- [Home Assistant iHealth integration](https://www.home-assistant.io/integrations/ihealth/) — cloud API only, not BLE

## Observed in adwatch (April 2026 Export)

| Field | Value |
|-------|-------|
| Local Name | `BP5S 11070` |
| Service UUID | `636F6D2E-6A69-7561-6E2E-425056323500` |
| Manufacturer Data | `590000000000004d323c1b68` |
| Company ID | `0x0059` (Andon Health) |
| Sighting Count | 191 over ~3 hours |
| RSSI Range | -83 to -100 dBm |

The device advertised continuously during the observation window, typical for a BLE medical device in standby/pairing mode.
