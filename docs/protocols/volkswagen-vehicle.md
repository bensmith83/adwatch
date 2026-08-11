# Volkswagen Vehicle (FE4C)

## Overview

**Volkswagen AG** holds SIG service-UUID `0xFE4C` (`member_uuids.yaml`).
Captured as a UUID-only advertisement — no manufacturer data, no
service data, no local name — at persistent far-RSSI: the typical
fingerprint of a parked vehicle's in-cabin BLE module.

VAG has not published the FE4C frame semantics, so the parser
attributes at the brand level only and labels candidate uses without
claiming a specific model.

## Likely Sources

| Source | Notes |
|---|---|
| MIB3 head unit | The infotainment platform in Golf 8 / ID.3 / ID.4 / Tiguan / Touareg (2020+) |
| We Connect / Car-Net TCU | Telematics control unit |
| Phone-as-key beacon | Newer VAG platforms with Digital Key support |
| Volkswagen Group SKUs broadly | Audi, ŠKODA, SEAT, CUPRA, Porsche — all part of VAG, but each typically holds its own SIG UUID in addition to or instead of the parent's |

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Service UUID | `0xFE4C` | Volkswagen AG — SIG-registered |
| Manufacturer data | *(absent in observed captures)* | |
| Service data | *(absent in observed captures)* | |
| Local name | *(absent in observed captures)* | |
| Address type | `random` | rotating BD_ADDR |

### What We Can Surface

| Field | Source | Notes |
|---|---|---|
| Vendor | hard-coded | `Volkswagen AG` |
| `sig_service_uuid` | hard-coded | `0xfe4c` |
| `likely_source` | hard-coded | `in_vehicle_ble_module` |
| `candidates` | hard-coded | "MIB3 head unit, We Connect / Car-Net TCU, phone-as-key beacon" |

### What We Cannot Surface from the Advertisement

- Specific model (Golf 8 vs ID.4 vs Tiguan vs Atlas …).
- Year / trim.
- Phone-pairing state, charging state (for EVs), lock state.
- Telematics / We Connect cloud connectivity state.
- Driver / owner identity.

All operational state requires either VW's MyVW / We Connect cloud
APIs (with the owner's credentials) or post-pair GATT access.

## Stable Identity

UUID-only advertisement → MAC-anchored stable key. Distinct trips by
the same vehicle will rotate to new MACs and appear as fresh
identities — that matches VAG's privacy intent.

```
stable_key = volkswagen_vehicle:<bd_addr>
identifier = SHA256(stable_key)[:16]
```

## Detection Significance

- A Volkswagen vehicle is in BLE range. Persistent long-RSSI dwell
  fits a parked car at curbside or in an adjacent parking structure.
- The parser is intentionally conservative — VW's brand portfolio
  spans Polo / Tiguan / Atlas / Golf / ID.3 / ID.4 / ID.7 / Touareg
  / Arteon and more. Without payload decoding, we surface "Volkswagen
  vehicle (model unknown)" rather than guessing.

## References

- [BT SIG `member_uuids.yaml`](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — confirms `0xFE4C` → Volkswagen AG
- [Blatann BT SIG UUID DB](https://blatann.readthedocs.io/en/latest/blatann.bt_sig.uuids.html) — cross-confirmation
- [Volkswagen Connect](https://connect.volkswagen.com/connectivity.html) — context on the BLE-adjacent connectivity products
