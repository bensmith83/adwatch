# Kohler Smart Bathroom Fixtures

## Overview

**Kohler Company** ships a connected-bathroom product line — **Anthem**
(digital shower controllers), **PerfectFill** (smart tub valves),
**Stillness** (experience tub), **Numi** (intelligent toilet),
**Dekoda** (health toilet seat, Kohler Health), **Sprig** (smart
shower), and the **Konnect** faucet family — all sharing the same BLE
advertising fingerprint.

Company ID `0x0E88` is officially registered to Kohler Company per the
BT SIG Assigned Numbers PDF (2025-03-13). It is sole-vendor — there is
no other registered slot holder — so CID 0x0E88 alone is a reliable
attribution signal.

(Kohler also holds `0x0EFE` for the UK subsidiary Kohler Mira Limited
and `0x12D5` for Kohler Ventures; this parser covers the parent
Company's `0x0E88` slot only.)

## Supported Products

| Product family | Notes |
|---|---|
| Anthem digital shower | DTV+, Anthem+ |
| PerfectFill | Smart tub valve |
| Stillness | Experience tub |
| Numi | Intelligent toilet (2.0) |
| Dekoda | Health toilet seat (Kohler Health) |
| Sprig | Smart shower head |
| Konnect | Smart faucet family (kitchen, bath) |

The parser doesn't attempt to distinguish specific SKU from the
advertisement alone — the 4-byte payload token surfaces as
`device_token` but isn't decoded to a product name.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0E88` | Kohler Company — sole-vendor SIG-registered |
| Mfg payload length | ≥ 4 bytes | first 4 bytes are a static per-device token |
| Service UUID | `DAF54901` (32-bit truncated) or `DAF54901-…` (128-bit) | Kohler vendor service base; CoreBluetooth sometimes returns the truncated 32-bit prefix |
| Local name | *(absent in observed captures)* | |
| Service data | *(absent in observed captures)* | |
| Address type | `random` | rotating private address |

Either path (CID 0x0E88 with mfg payload OR DAF54901 UUID) is
individually unambiguous; the parser matches either so sibling
ad frames that drop one signal are still recovered.

### Mfg Payload Layout (observed)

```
[0..1] 88 0E         CID 0x0E88 LE
[2..5] XX XX XX XX   per-device static token (e.g. 85 80 b7 94)
[6..7] 00 00         reserved zeros
```

The 4-byte token is the stable per-unit identifier — it survives BD_ADDR
rotation. Bytes 6-7 are constant zero in all observed captures; the
parser doesn't gate on them, leaving room for them to encode state in
firmware revisions we haven't captured.

### What We Can Surface

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Kohler Company` |
| `device_token` | mfg[2..5] | when CID path matches |
| `vendor_service_prefix` | hard-coded | `daf54901` |
| `company_id_hex` | hard-coded | `0x0e88` |

### What We Cannot Surface from the Advertisement

- Specific product SKU (Anthem vs Numi vs Sprig vs ...).
- Live state (shower on/off, tub fill %, toilet seat occupancy,
  flush state, Dekoda health-tracking output).
- Firmware version, Wi-Fi connectivity to Kohler Cloud.
- Maintenance / fault state.

All live state lives behind GATT on the `DAF54901-…` vendor service
and requires a connection plus an undocumented characteristic map.

## Stable Identity

`device_token` is the per-unit stable key when present (CID-path
captures); UUID-only sibling ads fall back to the rotating MAC:

```
stable_key = kohler_smart_bathroom:token:<8-hex>     (CID path)
stable_key = kohler_smart_bathroom:mac:<bd_addr>     (UUID-only fallback)
identifier = SHA256(stable_key)[:16]
```

## Detection Significance

- A Kohler smart-bathroom fixture is in range — strongly indicates a
  high-end residential or hospitality install. Kohler smart bath
  retails $500-$15,000+ per fixture.
- Multiple Kohler tokens at one site suggests a whole-bath or
  whole-building install (matched faucet + shower + tub).
- Dekoda specifically is a *health-tracking* toilet seat (urine
  analysis, body-composition); presence has weak health-privacy
  implications similar to other PII bath fixtures, though far less
  acute than e.g. continuous-monitoring devices.

## References

- [BT SIG Assigned Numbers PDF (2025-03-13)](https://btprodspecificationrefs.blob.core.windows.net/assigned-numbers/Assigned%20Number%20Types/Assigned_Numbers.pdf) — confirms 0x0E88 = Kohler Company
- [BT SIG company_identifiers.yaml](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
- [Kohler smart home product family](https://www.kohler.com/en/products/smart-home)
- [Kohler Health — Dekoda](https://www.kohlerhealth.com/dekoda/)
