# Unmodified ESP-IDF `gatts_demo` reference firmware

## Overview

Not a vendor protocol — a firmware-hygiene fingerprint. Some BLE product
ships Espressif's ESP-IDF GATT-server example application
(`examples/bluetooth/bluedroid/ble/gatt_server/main/gatts_demo.c`)
unmodified, so its BLE advertisement is the SDK example's own literal
placeholder constants rather than product-specific data. Verified against
the actual upstream source (checked master, v4.4.6, v5.1.2):

```c
static uint8_t test_manufacturer[TEST_MANUFACTURER_DATA_LEN]
    = {0x12, 0x23, 0x45, 0x56};
#define GATTS_SERVICE_UUID_TEST_A   0x00FF
#define GATTS_SERVICE_UUID_TEST_B   0x00EE
```

The leading two bytes of that array (`0x12, 0x23`) parse as a company ID
if you don't know better — `0x2312`, little-endian `12 23` — but it isn't
one. It's just the first two bytes of a hardcoded C array.

## BLE Advertisement Format

### Identification anchors (either is sufficient)

| Signal | Value | Notes |
|--------|-------|-------|
| Manufacturer data | `12 23 45 56 00 00` | The exact 4-byte SDK constant, zero-padded to 6 bytes by `esp_ble_gap_config_adv_data`'s length handling |
| Service UUID pair | `0x00EE` **and** `0x00FF` together | `GATTS_SERVICE_UUID_TEST_B` + `GATTS_SERVICE_UUID_TEST_A`. `0x00FF` alone is NOT a safe anchor — 9 unrelated records in one corpus sweep used it independently for other purposes; only the pair (or the manufacturer-data constant) identifies this specific example. |

### What we can extract

Nothing product-specific — by construction. `device_class: "unidentified"`,
`vendor: "unidentified"`. The only signal is "whoever built this didn't
customize the reference demo before shipping," which is itself sometimes
useful context (unfinished or copy-pasted firmware).

### What we cannot extract

- Vendor / product (there is none to extract — this is upstream SDK example
  code, not a product's own protocol)
- Any real payload — the constant carries no information

## Detection significance

- A concrete, reproducible false lead: the manufacturer-data bytes look
  exactly like a company ID at first glance (`0x2312`), and would waste
  investigation time on a "who is company 0x2312" chase if not recognized.
- A useful hygiene signal — recurring sightings of this exact fingerprint
  flag products still running unmodified reference firmware.

## References

- Espressif ESP-IDF, `examples/bluetooth/bluedroid/ble/gatt_server/main/gatts_demo.c`
  (`https://github.com/espressif/esp-idf`), confirmed present and unchanged
  across `master`, `v4.4.6`, and `v5.1.2`.
- Captures: `research/telemetry-merged.json`, 2026-07-30 sweep
  (`research/sweep-2026-07-30-candidates.md` in the app repo).
