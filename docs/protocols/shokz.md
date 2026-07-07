# Shokz Bone-Conduction Headphones Plugin

## Overview

Bluetooth SIG company ID `0x0CAC` is registered to **Shenzhen Shokz Co., Ltd.** — the bone-conduction headphone maker (formerly **AfterShokz**). Their products advertise this company ID with a friendly local name (`"OpenFit Air by Shokz"`, `"OpenComm 2"`, `"OpenRun Pro 2"`, `"Aeropex by AfterShokz"`, etc.).

## LE / pairing-mode advert (2026-07-06 sweep)

Besides the SIG `0x0CAC` frame, Shokz products also broadcast a BLE-mode name
`LE-<model>` (e.g. `LE-OpenRun Pro`) on a **pseudo/vanity CID** (observed
`0xF5A8`, not `0x0CAC`) with a *different, non-token* payload layout. The parser
now also routes on the **product-family name** — `^(LE-)?(OpenRun|OpenComm|
OpenFit|OpenMove|OpenSwim|Aeropex|Shokz|AfterShokz)\b` — anchored on specific
product tokens (not a bare "Open", to avoid colliding with the unrelated
`OpenGate` parser). On the name path we surface raw mfg only and do **not**
apply the `0x0CAC` 6-byte-token layout. (Low-trust-sourced — see the sweep write-up.)

## BLE Advertisement Format

| Signal | Value |
|---|---|
| Company ID | `0x0CAC` (Shenzhen Shokz Co., Ltd.), or a pseudo-CID on the LE-name path |
| Local name | Marketing model (`OpenFit *`, `OpenComm *`, `OpenRun *`, `Aeropex *`, `LE-OpenRun Pro`) |

### Manufacturer Data Layout (6 bytes after company ID)

```
Bytes 0..5: 6-byte rotating device token (changes between consecutive ads of the same headset)
```

The token is not the public MAC (CoreBluetooth doesn't expose that on iOS); it rotates so we don't use it as a stable identifier. Use the local name as the device identity.

## References

- [Shokz product line](https://shokz.com/)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
