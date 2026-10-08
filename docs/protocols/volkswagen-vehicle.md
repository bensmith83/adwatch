# Volkswagen Vehicle (FE4C / FE30 / FE31)

## Overview

**Volkswagen AG** holds SIG service-UUIDs `0xFE4C`, `0xFE30` and `0xFE31`
(`member_uuids.yaml`). FE4C is captured as a UUID-only advertisement — no
manufacturer data, no service data, no local name — at persistent
far-RSSI: the typical fingerprint of a parked vehicle's in-cabin BLE
module. FE30 / FE31 are the same class of emitter carrying a 22-byte
service-data frame (see below).

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

## FE30 / FE31 Service-Data Frame (2026-08-23 sweep)

First logged in the 2026-07-31 telemetry sweep as "two emitters, one
constant 22-byte blob" and parked pending a second VW sighting; the
2026-08 corpus added three more FE30 emitters and one FE31 (31 sightings),
all the same shape:

```
FE30: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx 0001 00000000   (emitter 1)
FE30: yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy 0001 00000000   (emitter 2)
FE30: zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz 0001 00000000   (emitter 3)
FE31: wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww 0303 00000000   (emitter 4)
      └─────────── 16-byte blob ──────┘ tag  trailer
```

| Offset | Size | Meaning |
|---|---|---|
| 0..15 | 16 | Opaque blob. Constant per emitter across BLE MAC rotation (three rotating-address records in July shared one blob), different for every emitter. Uniformly random-looking — most likely an encrypted / key-derived vehicle or key identifier. Not interpreted. |
| 16..17 | 2 | Frame tag: `00 01` on every FE30 frame, `03 03` on the FE31 frame. |
| 18..21 | 4 | Always `00 00 00 00`. |

Nothing public describes these frames; VW's phone-as-key / "Digital Key"
and the ID-series' app pairing are the plausible owners, but that is a
guess and the parser does not state it. Frames of any other length under
FE30 / FE31 fall back to the FE4C-style presence claim.

## Stable Identity

FE4C (and any malformed FE30/FE31): UUID-only advertisement →
MAC-anchored stable key. Distinct trips by the same vehicle will rotate
to new MACs and appear as fresh identities — that matches VAG's privacy
intent.

```
stable_key = volkswagen_vehicle:<bd_addr>
identifier = SHA256(stable_key)[:16]
```

FE30 / FE31 with the 22-byte frame: the blob is rotation-stable, so it
is the key (an all-zero or all-ones blob is treated as a placeholder and
falls back to the MAC). Note the privacy implication: a vehicle emitting
this frame is re-identifiable across address rotations by anyone
scanning.

```
stable_key = volkswagen_vehicle:fe30:<blob hex>      (or fe31)
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
