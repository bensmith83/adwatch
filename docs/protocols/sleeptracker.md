# SleepTracker (Beautyrest) BLE Protocol

## Overview

SleepTracker by Fullpower Technologies is a non-contact sleep monitor embedded in Beautyrest and Serta mattresses. It advertises via BLE using company ID 0x01EF and a custom service UUID for GATT communication. The device tracks sleep stages, breathing rate, and heart rate through sensors built into the mattress.

## Identifiers

- **Company ID:** `0x01EF` (Fullpower Technologies)
- **Service UUID:** `F6380280-6D90-442C-8FEB-3AEC76948F06` (custom GATT service)
- **Local name:** `SleepTracker`
- **Device class:** `health`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x01EF` | Fullpower Technologies |
| Service UUID | `F6380280-...` | SleepTracker GATT service |
| Local name | `SleepTracker` | Fixed name, no variant |

### Manufacturer Data Structure

Total: 10 bytes (2 company ID + 8 payload)

#### Example

```
ef 01 00 22 97 9b 3c 06 01 0f
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0-1 | 2 | `ef 01` | Company ID 0x01EF (little-endian) |
| 2 | 1 | `00` | Protocol version or status flag |
| 3 | 1 | `22` | Device state/mode indicator |
| 4-7 | 4 | `97 9b 3c 06` | Device identifier or rolling counter |
| 8-9 | 2 | `01 0f` | Firmware version or status flags |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | company_id, service_uuid | SleepTracker nearby |
| Device state | mfr_data byte 3 | Mode/state indicator |
| Device ID | mfr_data bytes 4-7 | Unique device identifier |
| Firmware info | mfr_data bytes 8-9 | Version or status |

### What We Cannot Parse (requires GATT connection or Beautyrest app)

- Sleep stage data
- Breathing rate
- Heart rate
- Sleep score
- Environmental data (temperature, humidity)

## Identity Hashing

```
identifier = SHA256("sleeptracker:{mac}")[:16]
```

## Detection Significance

- Indicates a bedroom with a Beautyrest/Serta smart mattress
- Always-on BLE advertisement when mattress has power
- Single fixed name per device (no model variants in advertisement)

## References

- [Beautyrest SleepTracker](https://www.beautyrest.com/sleeptracker) — product page
- [Fullpower Technologies](https://www.fullpower.com/) — company behind SleepTracker
- Company ID 0x01EF registered to Fullpower Technologies in Bluetooth SIG
