# BBPOS Plugin

## Overview

Bluetooth SIG company ID `0x02AB` is registered to **BBPOS Limited** (Hong Kong), a maker of small Bluetooth card readers / mPOS dongles. BBPOS hardware ships under its own brand and is also resold by acquirers like Stripe (Stripe Reader M2), Square (early generations), PayPal Here, and Zettle, and embedded into kiosks and vending integrations.

Two product families appear in the wild:

| Model code | Marketing name | Form factor |
|---|---|---|
| `STRM2D` | Stream 2D | Desktop / cradle reader (PIN + chip + NFC) |
| `CHB20`  | Chipper BT 2.0 | Handheld magstripe / EMV chip reader |

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Company ID | `0x02AB` (BBPOS Limited) |
| Service UUID | `0xFFA0` (user-defined; informational only — many unrelated products use this slot) |
| Local name | `<MODEL_CODE><SERIAL>` — e.g. `"STRM2D533004284"` or `"CHB20-1000003F1"` |

We match on company ID **or** a local name with one of the known model-code prefixes. We deliberately do **not** match on the `0xFFA0` service UUID alone because that 16-bit slot is in the user-defined range and is used by many unrelated white-label products.

### Manufacturer Data Layout (1 byte after company ID)

```
ab 02 | XX
──┬── ──┬──
 SIG    hardware / firmware revision tag (stable per emitter, surfaced as `payload_hex`)
```

Only a single byte of payload is observed. Its meaning is not publicly documented; we surface it raw.

### Local Name Format

```
<MODEL_CODE><[-]?><SERIAL>
```

- `STRM2D` followed directly by a 9-digit serial (e.g. `STRM2D533004284`)
- `CHB20` followed by `-` and a 9-character alphanumeric serial (e.g. `CHB20-1000003F1`)

The parser uses `(model_code, serial)` as the stable key: `bbpos:STRM2D:533004284`.

## References

- [BBPOS product line](https://www.bbpos.com/)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
