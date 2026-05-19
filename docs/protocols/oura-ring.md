# Oura Ring Plugin

## Overview

Bluetooth SIG company ID `0x02B2` is registered to **Oura Health Oy** (Finland), maker of the Oura Ring sleep / readiness tracker. The Ring exposes a proprietary primary service UUID `98ED0001-A541-11E4-B6A0-0002A5D5C51B` used by the Oura companion app for syncing nightly biometric data.

## BLE Advertisement Format

| Signal | Value |
|---|---|
| Company ID | `0x02B2` |
| Service UUID | `98ED0001-A541-11E4-B6A0-0002A5D5C51B` |
| Local name | `"Oura Ring 4"`, etc. |

### Manufacturer Data Layout (4 bytes after company ID)

```
Byte 0  : 0x04   — frame type (ring advertising)
Byte 1  : generation byte
Bytes 2..3: protocol / firmware revision (LE uint16, observed 0x0127)
```

### Generation Byte

| Code | Generation |
|---|---|
| `0x60` | Ring 4 |

Other generations expected to use different codes — to be confirmed as we capture more samples.

## References

- [Oura Ring product page](https://ouraring.com/)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
