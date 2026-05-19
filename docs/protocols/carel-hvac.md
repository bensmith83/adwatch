# Carel BLE HVAC / Refrigeration Controller Plugin

## Overview

Bluetooth SIG company ID `0x05B2` is registered to **CAREL Industries S.p.A.** (Italy), one of the major commercial HVAC / refrigeration controller vendors. Their BLE-enabled product family includes **iJW**, **Heez**, **μChiller**, **MPXone**, and **PJ-BLE** controllers. These pair with the Carel **APPLICA** smartphone app for commissioning and live status.

In our scans we observed a single nearby Carel controller broadcasting consistently (660+ sightings of `Carel_00000E6B03`), which suggests a stationary commercial deployment — exactly the use case AdWatch is designed to surface.

## BLE Advertisement Format

| Signal | Value |
|---|---|
| Company ID | `0x05B2` (Carel Industries S.p.A.) |
| Local name | `"Carel_<10-16 hex chars>"` (the controller's asset ID) |
| Eddystone-UID | Optional — same `0E6B03`-style instance ID on service `0xFEAA` |

### Manufacturer Data Layouts

Two frame shapes are observed:

**Long form (10 bytes after company ID):**
```
Bytes 0..3: 02 00 02 00 — protocol version
Bytes 4..9: 6-byte controller serial (LE)
```

**Ping form (2 bytes after company ID):**
```
Bytes 0..1: 02 00 — heartbeat-only, no serial
```

The controller also commonly broadcasts an Eddystone-UID frame on service UUID `0xFEAA` carrying the same 10-character asset ID that appears in the local name; that frame is handled by `EddystoneParser`.

## Detection Significance

- **Commercial HVAC / refrigeration deployments.** Cold-chain warehouses, supermarket refrigeration, pharmacy fridge banks, commercial AC chillers.
- **Stable asset ID broadcast in plaintext.** The 10-character ID appears in both the local name and the Eddystone instance ID, so anyone with a BLE scanner can enumerate Carel controllers in a facility.

## References

- [Carel BLE-enabled HVAC products](https://www.carel.com/apps)
- [Carel APPLICA app](https://www.carel.com/apps)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
