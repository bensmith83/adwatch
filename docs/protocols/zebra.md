# Zebra Technologies BLE Protocol

## Overview

Zebra Technologies enterprise mobile computers and barcode scanners advertise via BLE using the assigned service UUID FE79. These devices are ubiquitous in retail environments (grocery stores, pharmacies, warehouses) where they serve as handheld barcode scanners, inventory management terminals, and point-of-sale devices.

## Identifiers

- **Service UUID:** `FE79` (Bluetooth SIG assigned to Zebra Technologies)
- **Local name pattern:** `{store}_{dept}{device}` (retailer-configured)
- **Device class:** `barcode_scanner`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `FE79` | Zebra Technologies assigned UUID |
| Local name | Varies | Retailer-configured device identifier |

### Local Name Convention

The local name is configured by the retailer's IT team (via Zebra StageNow or Enterprise Home Screen) and encodes organizational information:

| Example Name | Store | Department | Device |
|--------------|-------|------------|--------|
| `096_PDZebra1` | 096 | PD (Produce) | Zebra1 |
| `096_PDZebra2` | 096 | PD (Produce) | Zebra2 |
| `096_PharmZebra` | 096 | Pharm (Pharmacy) | Zebra |
| `096_CA_CAC` | 096 | CA (Checkout Area) | CAC |
| `096_CA_Floral` | 096 | CA (Checkout Area) | Floral |

Known department codes:
- **PD** — Produce Department
- **Pharm** — Pharmacy
- **CA** — Checkout Area

### Advertisement Payload

The FE79 advertisements observed carry no service data payload — they function as presence beacons for Zebra's Device Tracker cloud service (indoor location/proximity tracking). The payload format is proprietary and undocumented.

### Device Types

Common Zebra enterprise devices that use FE79:
- **TC series**: TC21, TC26, TC52, TC57, TC72, TC77 (handheld touch computers)
- **MC series**: MC2200, MC2700, MC3300, MC9300 (mobile computers with integrated scanners)
- **EC series**: EC30, EC50, EC55 (enterprise companions)

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid FE79 | Zebra device nearby |
| Store number | local_name prefix | First numeric segment |
| Department | local_name middle | Department code after store number |
| Device name | local_name suffix | Device identifier within department |

### What We Cannot Parse (requires GATT connection or enterprise API)

- Device model (TC52, MC3300, etc.)
- Battery level
- Firmware version
- Scanner status
- Inventory/scan data

## Identity Hashing

```
identifier = SHA256("zebra:{mac}")[:16]
```

## Detection Significance

- Indicates proximity to a retail store or warehouse environment
- Multiple Zebra devices = likely inside a store
- Department codes reveal store layout/organization
- High sighting counts indicate persistent enterprise deployment

## References

- [Zebra Technologies](https://www.zebra.com/) — manufacturer
- [Bluetooth SIG FE79](https://www.bluetooth.com/specifications/assigned-numbers/) — assigned to Zebra Technologies
- [Zebra Device Tracker](https://www.zebra.com/us/en/software/mobile-computer-software/device-tracker.html) — BLE-based device location service
