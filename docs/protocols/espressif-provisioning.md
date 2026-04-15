# Espressif BLE Provisioning Service

## Overview

Espressif's ESP-IDF includes a "Unified Provisioning" framework (`wifi_prov_mgr` / `protocomm`) used by the vast majority of ESP32-family Wi-Fi devices to onboard onto a user's home network. The BLE transport advertises a fixed 128-bit service UUID — `021A9004-0382-4AEA-BFF4-6B3F1C5ADFB4` — together with a one- to two-character device-name suffix (e.g. `PROV_AB12`).

Although the UUID is "custom", it is shipped in the ESP-IDF source tree and is therefore present on millions of devices: smart plugs, lightbulbs, robot vacuums, ambient sensors, ESPHome devices, third-party IoT products, hobby projects. Whenever you see this UUID, the broadcaster is an ESP32-class device sitting in unprovisioned mode (or in a re-provisioning window).

## Identifiers

- **Service UUID:** `021A9004-0382-4AEA-BFF4-6B3F1C5ADFB4` (128-bit, hard-coded in ESP-IDF)
- **Common local name patterns:** `PROV_xxxx`, `BLUFI_xxxx`, `ESP_xxxx`, vendor-specific (often empty)
- **Device class:** `provisioning`

## Source Reference

In ESP-IDF, the service UUID is defined as:

```c
// components/protocomm/src/transports/protocomm_ble.c
static const uint8_t adv_service_uuid128[16] = {
    0xfb, 0x34, 0x9b, 0x5f, 0x80, 0x00, 0x00, 0x80,
    0x00, 0x10, 0x00, 0x00, 0x04, 0x90, 0x1a, 0x02,
};
```

Read big-endian: `021A9004-0382-4AEA-BFF4-6B3F1C5ADFB4` (with the BLE base UUID convention applied).

The companion characteristic UUIDs in the same range:
- `021A9001-...` — `prov-session`
- `021A9002-...` — `prov-config`
- `021A9003-...` — `proto-ver`
- `021A9000-...` — vendor custom endpoint

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `021A9004-0382-4AEA-BFF4-6B3F1C5ADFB4` | Fixed in ESP-IDF |
| Service Data | none / empty | Endpoint data is read over GATT after connect |
| Manufacturer Data | optional | Some vendors add 0x02E5 (Espressif Inc.) frame |
| Local name | varies | `PROV_xxxx` is the SDK default |

### Advertisement Frame

A typical frame is just the service UUID with no payload:

```
Service UUIDs: [021A9004-0382-4AEA-BFF4-6B3F1C5ADFB4]
Service Data:  {}
Local name:    "" / "PROV_AB12" / vendor-set
```

There is no telemetry in the advertisement itself — all data exchange happens after a GATT connect via the protocomm endpoints.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device family | service_uuid | Always ESP32-class |
| Device state | presence | "Currently unprovisioned" / "in setup" |
| Device hint | local_name | Vendor-supplied, often `PROV_xxxx` |

### What We Cannot Parse (requires GATT connect)

- Wi-Fi scan results (over `prov-config`)
- Device capabilities (`proto-ver`)
- Vendor extensions (`021A9000-...`)
- Real product / model identification

## Sample Advertisement

```
Anonymous ESP32 in setup mode:
  Service UUIDs: ["021A9004-0382-4AEA-BFF4-6B3F1C5ADFB4"]
  Service Data:  {}
  Manufacturer:  none
  Local name:    ""
  Sightings:     31918   (single highly-active device on the test bench)
```

## Identity Hashing

```
identifier = SHA256("espressif_prov:{mac}")[:16]
```

(Provisioning advertisements often use a randomized resolvable private address. Hashing on MAC is the best we can do; the same physical device may appear as multiple identities across reboots.)

## Detection Significance

- Indicates an ESP32-class device sitting in unprovisioned mode within radio range
- Could be: smart plug, bulb, sensor, robot vacuum, ESPHome project, hobby board
- A persistent / always-on advertisement implies a device that was never successfully onboarded — possibly a failed setup or a device that was factory-reset and forgotten
- Useful as a "neighbour audit": newly-appearing PROV beacons hint that someone nearby is unboxing a smart-home device

## Parsing Strategy

1. Match on `service_uuid == "021a9004-0382-4aea-bff4-6b3f1c5adfb4"` (case-insensitive)
2. If `local_name` is set, capture it as `device_hint`
3. If `manufacturer_data` company_id is `0x02E5` (Espressif Inc.), capture as `vendor_confirmed=true`
4. Return device class `provisioning`

## References

- [ESP-IDF protocomm BLE transport source](https://github.com/espressif/esp-idf/blob/master/components/protocomm/src/transports/protocomm_ble.c) — UUID definition
- [ESP-IDF Wi-Fi Provisioning](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/provisioning/wifi_provisioning.html)
- [esp-idf-provisioning-android](https://github.com/espressif/esp-idf-provisioning-android) — reference Android client
- Bluetooth SIG Company ID: `0x02E5` = Espressif Incorporated
