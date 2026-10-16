# Berner International air curtain (IntelliSwitch)

## Overview

**Berner International LLC** is a US manufacturer of commercial **air
curtains** (the warm/cold air barriers over store and loading-dock
entrances). Their **IntelliSwitch** controllers have built-in Bluetooth
and pair with the **Berner AIR** mobile app for commissioning and
control.

Berner holds Bluetooth SIG **company ID `0x0875`** (verified in the SIG
company-identifier registry). The unit observed in the wild advertises
with that CID and a model / part-number local name **`218542A01`**.

This is a **HIGH-confidence vendor attribution** (registered CID +
distinctive model name + cross-day frame skeleton) but
**identification-only**: the manufacturer payload is almost entirely
static and carries no decodable telemetry.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Company ID | `0x0875` | Berner International LLC (SIG-registered) |
| Local name | `218542A01` exactly | Berner model / part number — present on only 3 of 22 corpus records (lives in a scan response most sightings don't capture) |
| Manufacturer data | 26 bytes incl. CID | see layout below |
| Address type | `random` | rotates on-air |

**Either** of two paths matches (v1.1, 2026-10-08 sweep):

1. **Named path (original):** CID `0x0875` **plus** the exact model name
   `218542A01`. SIG company IDs can be cloned or inherited from a chipset
   vendor, so the CID alone is not trusted; CID + exact name together
   form the fingerprint.
2. **Structural fallback (v1.1):** CID `0x0875` **plus nameless** plus a
   24-byte payload matching the constant skeleton below. The full-history
   corpus shows 22 records / 122 sightings / 4 capture days
   (2026-06-27 → 2026-10-02) of this frame family — 19 of them nameless —
   with three named exemplars anchoring the family, so a nameless
   skeleton match is attributable without the name. The fallback
   requires the name to be **absent**: an owner-renamed unit stays
   unclaimed rather than letting a user-set string ride the fingerprint.

### Manufacturer-data layout (26 bytes, includes the 2-byte CID)

| Bytes (full mfg) | Value | Meaning |
|---|---|---|
| 0..1 | `75 08` | CID `0x0875` (Berner International) LE |
| 2..25 | 24-byte payload | overwhelmingly static; see below |

Three observed captures (full mfg, including CID):

```
75081f5d244d2c6e82 9a4ce5de13 da 34 42 1fbd825205cf904b26
75081f5d244d2c6e80 9a4ce5de13 da 34 42 1fbd825205cf904b26
75081f5d244d2c6e8e 9a4ce5de13 db 34 11 1fbd825205cf904b26
```

### Constant skeleton vs varying region (22 corpus records, 4 days)

Across the full-history corpus (22 records / 122 sightings / 4 capture
days 2026-06-27 → 2026-10-02), **17 of the 24 payload bytes are
constant** and form the structural skeleton the v1.1 fallback gates on:

| Payload offsets | Value | Notes |
|---|---|---|
| 0–5  | `1f 5d 24 4d 2c 6e` | constant 22/22 |
| 7–8  | `9a 4c` | constant |
| 10–11 | `de 13` | constant |
| 13   | `34` | constant |
| 16   | `bd` | constant |
| 20–23 | `cf 90 4b 26` | constant |

The **varying region** is opaque state/sequence material:

| Payload offset | Observed values | Notes |
|---|---|---|
| 6  | `80 82 8a 8e 94 96` | per-capture-day value |
| 9  | `e1` / `e5` | unit/config discriminator (June units `e5`) |
| 12 | `b0 b1 da db` | |
| 14 | `11 32 33 35 36 41 42 4d 6b 6c` | cycles within a capture day |
| 15 | `18 1c 1e 1f` | |
| 17–19 | `82 52 05` (June units) / `fb 72 06` (Aug–Oct units) | variant word |

We do **not** attempt to decode this region — there is no evidence it
encodes any user-meaningful state, and it may be a message
counter/authentication tag.

### What we can surface

| Field | Source | Notes |
|---|---|---|
| `vendor` | hard-coded | `Berner International` |
| `product` | hard-coded | `air curtain (IntelliSwitch controls)` |
| `model` | localName / hard-coded | `218542A01` (named path) or `218542A01 family (nameless, structure-matched)` (fallback) |
| `company_id` | hard-coded | `0x0875` |
| `payload_hex` | mfg bytes 2..25 | manufacturer payload (CID stripped) |
| `rotating_field_note` | hard-coded | notes the opaque varying region |
| `attribution` | hard-coded | `id_only` (named) / `fingerprint` (structural) |
| `match_basis` | hard-coded | `local_name` (named) / `structure` (fallback) |

### What we cannot surface

- Temperature, fan speed, heater/door state, schedules — these require
  the Berner AIR app's GATT connection and vendor characteristic map;
  none are present in the broadcast advertisement.
- A durable per-unit identifier (see below).

## Stable identity

There is **no per-unit identifier** in the advertisement. The model name
`218542A01` is a part number shared across every unit of this model, and
the BLE on-air address is random/rotating — so two captures of the same
physical unit cannot be reliably linked, and two different units sharing
the model name would collide on name. The stable key therefore falls
back to the (rotating) BLE address and is **not durable**:

```
stable_key = berner_air_curtain:<ble_address>   (not durable; address rotates)
identifier = SHA256(stable_key)[:16]
```

## Detection significance

- Flags commercial-HVAC infrastructure (air-curtain controllers at
  building entrances / loading docks) — useful for distinguishing
  fixed-facility equipment from transient consumer/visitor devices.
- The dual CID + model-name gate keeps the parser from claiming
  unrelated devices that happen to reuse CID `0x0875`.
- Identification-only: presence/vendor is reportable, but no operating
  state can be inferred from the passive advertisement.

## References

- [Bluetooth SIG company_identifiers.yaml](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — CID `0x0875` = Berner International LLC
- [Berner International — air curtains](https://www.berner.com/) — IntelliSwitch controls / Berner AIR app
- Captures: `research/nearsight_export 7.json` (~6 sightings, 1 device, localName `218542A01`, three rotating-field variants); full-history telemetry corpus 2026-06-27 → 2026-10-02 (22 records / 122 sightings / 4 capture days, 3 named + 19 nameless records) — see `research/sweep-2026-10-08-candidates.md` in the app repo.
