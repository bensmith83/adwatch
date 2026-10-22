# Vuzix Z100 HUD Smart Glasses

## Overview

The **Vuzix Z100** monochrome HUD glasses ("Ultralite" SDK; app
`com.vuzix.connect`, pure Java) are discovered **purely by advertised 128-bit
service UUID** — no manufacturer data, no service data, no name filter. The
advert also exposes one state bit: **normal vs firmware-update (DFU) mode**.

## BLE Advertisement Format

### Identification

| Signal | Value | Meaning | Notes |
|--------|-------|---------|-------|
| Service UUID | `39191400-BFC2-4BEE-A81A-28C23B6AC84A` | Normal Z100 (Ultralite command transport) | Vuzix-specific; `i5/y0.java:31`, matched `i5/a1.java:41,44-50` |
| Service UUID | `0xFE59` (Nordic Semiconductor Secure DFU) | Z100 in DFU mode | Generic Nordic DFU UUID — attribute to Z100 only with MAC corroboration (same address previously advertised `39191400`); `i5/y0.java:32`, `i5/a1.java:42,52-58` |
| Company ID / name | — | — | Not used |

The scan callback also checks GAP discoverable flags and bond state
(`i5/a1.java:39`) but gates on the UUID.

## What We Can Parse from Advertisements

| Field | Source |
|-------|--------|
| Device presence | `39191400-…` UUID |
| `dfu_mode` | `FE59` advertised instead of `39191400` |

## What Requires GATT

Battery `0x2A19`, serial `0x2A25`, model `0x2A24`, and all HUD content.

## Identity Hashing

No in-advert ID: `SHA256("vuzix-z100:{mac}")[:16]`.

## Detection Significance

Unambiguous HUD-glasses wearer presence; DFU-state leak (device mid-update).
No serial broadcast, so tracking reduces to MAC behaviour.

## adwatch Status

No plugin; not covered by `smart_glasses.py`. Future match: service UUID
`39191400-bfc2-4bee-a81a-28c23b6ac84a`; `FE59` only as a DFU flag on an address
already attributed to a Z100. Report confidence: HIGH.

## References

- apk-ble-hunting `reports/vuzix-connect_passive.md` (and `reports/vuzix-connect.md`)
- Code cited by the report: `i5/a1.java:34-58` (scan callback), `i5/y0.java:31-32` (UUIDs)
