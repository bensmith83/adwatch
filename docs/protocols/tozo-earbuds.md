# TOZO Earbuds Plugin

## Overview

[TOZO](https://www.tozostore.com/) is a Chinese-OEM consumer-audio brand whose true-wireless earbuds — T-series (`T6`, `T10`, `T12`), NC-series ANC models (`NC2`, `NC7 Pro`, `NC9`) and the premium `Golden X1` — are best-selling sub-$50 fixtures on Amazon US. The firmware is built on **Airoha** reference chips (AB1562 / AB155x), and inherits Airoha's habit of stuffing a randomized blob into the BLE manufacturer-specific-data slot without prepending a real Bluetooth SIG company identifier.

This parser ignores the bogus 2-byte "company ID" prefix (we observe different values per unit — `0xFC58`, `0x4B94`, … — none of them are in the SIG-assigned range, which currently caps at `0x10C7`) and identifies strictly on the `"TOZO "` local-name prefix.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Local name | `^TOZO ` (e.g. `"TOZO T6"`, `"TOZO NC9"`, `"TOZO Golden X1"`) |
| Company ID | **Spoofed / random.** Different per unit, none SIG-assigned. **Not** a valid signal — `0xFC58` and `0x4B94` are well above the highest assigned `0x10C7`. |
| Service UUIDs | _none observed_ — connection-time only. |

### Manufacturer Data Layout (9 bytes, opaque)

```
Bytes 0..8: 9-byte random-looking blob, e.g. "58fcc6f286d3845752" or "944bf84b6219b15752"
            - Bytes 0..1: looks like a CID but is just the first two payload bytes;
              varies arbitrarily across units.
            - Bytes 7..8 ("57 52"): observed identical across both sampled units
              — likely a fixed family/firmware marker. Not yet validated across
              the full product line.
            - Bytes 2..6: per-unit random / probably MAC- or session-derived.
```

The full mdata is surfaced as `payload_hex` in metadata so the trailing-marker observation can be confirmed against additional captures.

### Local Name Format

`TOZO <MODEL>`

- `<MODEL>` is the marketing model literal, space-separated from the brand. May contain internal whitespace (`Golden X1`).
- The TOZO companion app and Amazon pairing instructions reference this scheme consistently across the product line.

## Detection Significance

- **Cheap Airoha-based TWS in the wild.** TOZO advertisements are common indoors in shared offices and dorms. Their pattern is also a useful proxy for "low-end Airoha-firmware TWS" in general — other Chinese-OEM earbud brands using the same reference firmware show similar opaque blobs (without the `"TOZO "` name prefix).
- **No stable identifier per unit.** TOZO uses random BD_ADDR and the mdata payload appears to rotate per advertisement batch. We anchor the stable key on the MAC currently observed — this means a re-randomization will mint a new identity. That's acceptable: TWS earbuds are short-lived ad sources (active only when out of the case).

## What We Cannot Parse from Advertisements

- Battery / charging / connection state — only available over GATT after the TOZO app has paired the buds.
- Firmware version — same.
- Whether ANC / Transparency mode is active — same.

## References

- [TOZO product catalog](https://www.tozostore.com/collections/earbuds)
- [TOZO T6 product page](https://www.tozostore.com/products/t6)
- [TOZO NC9 product page](https://www.tozostore.com/products/2024-hybrid-active-noise-cancelling-wireless-earbuds)
- [TOZO Golden X1](https://www.tozostore.com/products/golden-x1)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — confirms `0xFC58` / `0x4B94` are not assigned.
- [Airoha (chip vendor used by TOZO)](https://english.cw.com.tw/article/article.action?id=3257)
