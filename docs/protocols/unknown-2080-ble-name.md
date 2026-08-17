# Unknown BLE Family — Service UUID `0x2080` + `"BLE_<mac>"` Local Name

## Overview

A BLE family fingerprinted on two co-occurring signals: 16-bit service
UUID `0x2080` (confirmed absent from all four Bluetooth SIG UUID
registries — service_uuids, member_uuids, characteristic_uuids,
company_identifiers — a non-SIG vendor value) and a local name matching
`BLE_<12 hex chars>` exactly.

Attribution is withheld at the product level: the 12 hex characters in the
local name read as a MAC address. Checking the first 3 bytes as an OUI
position, roughly **half** the observed units resolve to a genuine,
unicast IEEE OUI — **Shenzhen KKM** (a component/module vendor, not
necessarily the retail brand) — while the **other half** have the
multicast bit set, which by definition rules out a real assigned OUI
(locally-administered / synthetic). Because the lead only applies to half
the family, `vendor` stays `Unknown` at the product level and the OUI lead
is surfaced only in `attribution_note`, explicitly scoped to the
OUI-valid sub-family.

## Fingerprint

### Service UUID

| UUID | Notes |
|------|-------|
| `0x2080` | Non-SIG, vendor-specific 16-bit UUID |

### Local Name

| Pattern | Notes |
|---------|-------|
| `BLE_<12 hex chars>` | e.g. `BLE_BC57291E4EDC`, `BLE_DD34020AAE19` |

MAC-prefix split (first 3 bytes of the embedded hex):

| Prefix example | OUI lookup | Interpretation |
|---|---|---|
| `BC:57:29` | Shenzhen KKM (real, unicast) | genuine factory MAC, module-vendor lead only |
| `DD:34:02` | no match; multicast bit set | synthetic / locally-administered, not a real OUI |

### Service Data (6 bytes)

Verified across all 9 observed records (sweep 2026-07-17), including a
same-device repeat sighting 51 seconds apart that reproduced bytes 2–5
exactly:

```
byte[0]  byte[1]  bytes[2..5]
 XX       04       XX XX XX XX
 │        │              │
 │        │              └─ stable per physical device; ff ff ff ff
 │        │                 observed on 2 different devices — read as
 │        │                 an uninitialized/default sentinel
 │        └─ constant across all 9 records
 └─ increments per-device over time (confirmed via the repeat sighting);
    does NOT correlate across devices — a per-device counter or uptime
    tick, not a type/length tag
```

No correlation was found between `bytes[2..5]` and the name-embedded MAC
hex (checked both direct and byte-reversed comparisons).

## Identification

- **Primary**: service data present under UUID `0x2080` (exactly 6 bytes)
  **and** local name matches `BLE_<12hex>`. Both required.
- **Device class**: `unknown` — fingerprint-only, no product claim.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| `embedded_mac_hex` | local name | the 12-hex segment after `BLE_` |
| `counter_byte_hex` | serviceData byte 0 | per-device, non-comparable across devices |
| `header_byte_hex` | serviceData byte 1 | constant `04` |
| `tail_hex` | serviceData bytes 2-5 | stable per device; semantics unknown |
| `tail_state` | derived | flagged `default_sentinel` when tail is `ffffffff` |
| `attribution_note` | derived | the Shenzhen KKM OUI lead, scoped to the OUI-valid sub-family only |

## What We Cannot Parse

- Product / brand identity — attribution withheld at the product level.
- `tail_hex` semantics beyond "stable per device, sentinel when all-`ff`".
- Why roughly half the units carry a synthetic MAC in the name field.

## Stable Identity

Anchored on the BLE MAC — `stable_key = unknown_2080_ble_name:<mac>`.

## References

- Bluetooth SIG UUID registries (service_uuids, member_uuids,
  characteristic_uuids, company_identifiers YAML mirrors) — confirms
  `0x2080` absent from all four.
- IEEE OUI registry mirror — confirms `BC:57:29` = Shenzhen KKM (real,
  unicast) and `DD:34:02` has no assignment (multicast bit set, so by
  definition cannot be a real OUI).
