# Shokz Bone-Conduction Headphones Plugin

## Overview

Bluetooth SIG company ID `0x0CAC` is registered to **Shenzhen Shokz Co., Ltd.** — the bone-conduction headphone maker (formerly **AfterShokz**). Their products advertise this company ID with a friendly local name (`"OpenFit Air by Shokz"`, `"OpenComm 2"`, `"OpenRun Pro 2"`, `"Aeropex by AfterShokz"`, etc.).

## BLE Advertisement Format

| Signal | Value |
|---|---|
| Company ID | `0x0CAC` (Shenzhen Shokz Co., Ltd.) |
| Local name | Marketing model (`OpenFit *`, `OpenComm *`, `OpenRun *`, `Aeropex *`) |

### Manufacturer Data Layout (6 bytes after company ID)

```
Bytes 0..5: 6-byte rotating device token (changes between consecutive ads of the same headset)
```

The token is not the public MAC (CoreBluetooth doesn't expose that on iOS); it rotates so we don't use it as a stable identifier. Use the local name as the device identity.

## References

- [Shokz product line](https://shokz.com/)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
