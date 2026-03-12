# Medical EKG Devices

## Overview

Portable EKG/ECG monitors broadcast BLE advertisements to enable pairing with companion mobile apps. These devices are identified by their `local_name` pattern (`EKG-XX-XX-XX`) which encodes part of the device's MAC address.

adwatch detects these via advertisement local name only — no GATT connection is made. The presence of an EKG device is itself an interesting signal (medical device nearby).

## BLE Advertisement Format

### Identification

- **Local name pattern:** `^EKG-` (regex)
- **Example names:** `EKG-99-23-4c`, `EKG-A1-B2-C3`
- **Custom service UUIDs advertised:** `021a9004-0382-4aea-bff4-6b3f1c5adfb4`, `7aebf330-6cb1-46e4-b23b-7cc2262c605e`

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | local_name match | EKG device is nearby |
| Partial MAC | local_name suffix | `EKG-99-23-4c` → MAC ends in `99:23:4C` |
| Service UUIDs | service_uuids list | Custom UUIDs identify the manufacturer/protocol |

### What We Cannot Parse (requires GATT)

- WiFi SSID the device is connected to
- IP address
- Firmware version
- Actual EKG readings

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

The local_name contains a stable device identifier (MAC suffix), so this produces a consistent hash for the same physical device even across BLE MAC rotations.

## Detection Significance

- Indicates a medical monitoring device is nearby
- Could indicate a healthcare setting or a person with a cardiac condition
- The custom service UUIDs (`021a9004-...`) could help identify the specific manufacturer

## Known Manufacturers

The custom service UUID base `021a9004-0382-4aea-bff4-6b3f1c5adfb4` has been observed on consumer EKG monitors. Exact manufacturer identification requires further research.

## Future Work

- Identify specific EKG manufacturers from service UUID patterns
- Determine if manufacturer_data contains model information
- Catalog additional medical device advertisement patterns (pulse oximeters, blood pressure monitors, etc.)
