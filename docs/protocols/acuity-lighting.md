# Acuity Brands commercial lighting controls (CID 0x0346)

## Overview

**Acuity Brands Lighting, Inc.** is a US commercial/industrial lighting
vendor; its controls brands include **nLight**, **SensorSwitch** and
**Lithonia** lighting-control systems (occupancy sensors, wall
controllers, fixture controllers for commercial buildings). Acuity holds
Bluetooth SIG **company ID `0x0346`** (verified in the SIG
company-identifier registry).

The observed frames are nameless, service-less 18-byte manufacturer-data
broadcasts — a presence/config beacon from installed lighting-control
hardware. This is a **HIGH-confidence vendor attribution** (SIG-registered
CID + a consistent frame skeleton across two capture months) but
**identification-only**: no named capture and no public byte-format doc
exist, so the varying bytes are surfaced raw with no semantic claim.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Company ID | `0x0346` | Acuity Brands Lighting, Inc. (SIG-registered) |
| Manufacturer data | 20 bytes incl. CID (18-byte payload) | see layout below |
| Payload marker | `06 2e 00` at payload offsets 0–2 | constant 5/5 family records |
| Mid-field | `03 02 10` at payload offsets 9–11 | constant 5/5 |
| Trailer | `00 00` at payload offsets 16–17 | constant 5/5 |
| Local name | *(absent in all observed captures)* | |
| Service UUIDs | *(absent)* | |
| Address type | `random` | |

The parser requires CID `0x0346` **and** the 18-byte length **and** all
three constant regions — a squatter on the registered CID would need the
full skeleton to false-positive.

### Manufacturer-data layout (20 bytes, includes the 2-byte CID)

| Bytes (full mfg) | Value | Meaning |
|---|---|---|
| 0–1 | `46 03` | CID `0x0346` (Acuity Brands) LE |
| 2–4 | `06 2e 00` | frame-type marker (constant) |
| 5–7 | state bytes | observed `{00 28 10}`, `{02 2c 30}`, `{1e 28 30}` |
| 8–9 | `03 07` | constant |
| 10 | state byte | `15` or `fa` |
| 11–13 | `03 02 10` | constant mid-field |
| 14–17 | status region | `ff fe ff ff` (dominant static frame) / `01 34 23 1b` / `00 20 23 1b` — note the shared `23 1b` tail on the last two |
| 18–19 | `00 00` | constant trailer |

Corpus frames (full mfg, including CID):

```
4603062e00002810030715030210fffeffff0000   (27 sightings, 3 receivers — byte-identical)
4603062e001e28300307fa0302100134231b0000   (5 sightings)
4603062e00022c300307fa0302100020231b0000   (1 sighting)
```

### Unclaimed sibling frame

One additional frame under the same CID does **not** match the skeleton
and is deliberately not claimed:

```
460307000cb98e021401   (10 bytes incl. CID; 3 sightings, 2026-08-11 only)
```

Different length, different shape, single capture — noted for the
watchlist; a second capture day or a named record would justify a
sibling gate.

### What we can surface

| Field | Source | Notes |
|---|---|---|
| `vendor` | hard-coded | `Acuity Brands Lighting, Inc.` |
| `company_id` | hard-coded | `0x0346` |
| `state_3_hex` / `state_4_hex` / `state_5_hex` / `state_8_hex` | payload bytes 3/4/5/8 | raw echo — semantics unknown |
| `status_region_hex` | payload bytes 12–15 | raw echo — semantics unknown |
| `payload_hex` | mfg bytes 2–19 | manufacturer payload (CID stripped) |
| `attribution` | hard-coded | `fingerprint` |
| `decode` | hard-coded | `header_only` |

### What we cannot surface

- Fixture type / product model (no named capture exists).
- Occupancy, dim level, relay state, daylight readings — the varying
  bytes plausibly encode some of this, but with no labelled capture any
  assignment would be speculation.
- A durable per-unit identifier (see below).

## Stable identity

The dominant frame is **byte-identical across units** (uploaded by three
distinct receivers) and the BLE on-air address is random/rotating, so no
per-unit key exists in the advertisement. The stable key falls back to
the (rotating) BLE address and is **not durable**:

```
stable_key = acuity_lighting:<ble_address>   (not durable; address rotates)
identifier = SHA256(stable_key)[:16]
```

## Parser scope

Passive observation only. No GATT connection, pairing, or control is
performed or implied; lighting-control configuration requires the
vendor's tools.

## Confidence

- **Attribution: HIGH** — CID `0x0346` is Acuity Brands Lighting's own
  SIG slot (not a vanity/foreign value), and the frame skeleton is
  consistent across two capture days two months apart.
- **Field semantics: LOW (surfaced raw)** — no named capture, no public
  format documentation; the `state_*` / `status_region` fields are
  reported as hex without interpretation.

## References

- [Bluetooth SIG company_identifiers.yaml](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — CID `0x0346` = Acuity Brands Lighting, Inc.
- [Acuity Brands](https://www.acuitybrands.com/) — nLight / SensorSwitch / Lithonia lighting controls
- Captures: merged telemetry corpus 2026-08-11 + 2026-10-03 (6 records / 36 sightings) — see `research/sweep-2026-10-08-candidates.md` in the app repo.
