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
distinctive model name) but **identification-only**: the manufacturer
payload is almost entirely static and carries no decodable telemetry.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Company ID | `0x0875` | Berner International LLC (SIG-registered) |
| Local name | `218542A01` exactly | Berner model / part number |
| Manufacturer data | 26 bytes incl. CID | see layout below |
| Address type | `random` | rotates on-air |

**Both** signals are required to match. SIG company IDs can be cloned or
inherited from a chipset vendor, so CID `0x0875` alone is not trusted;
the registered CID **plus** the exact model name `218542A01` together
form the fingerprint.

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

The payload is **predominantly static**: of the 24 payload bytes, only
**3 change** across captures — full-mfg offsets **8, 14, 16** (payload
offsets 6, 12, 14). This looks like an opaque rotating / sequence / MIC
field. Everything else is constant.

### Rotating field

| Full-mfg offset | Payload offset | Observed values |
|---|---|---|
| 8  | 6  | `82` / `80` / `8e` |
| 14 | 12 | `da` / `da` / `db` |
| 16 | 14 | `42` / `42` / `11` |

We do **not** attempt to decode this field — there is no evidence it
encodes any user-meaningful state, and it may be a message
counter/authentication tag.

### What we can surface

| Field | Source | Notes |
|---|---|---|
| `vendor` | hard-coded | `Berner International` |
| `product` | hard-coded | `air curtain (IntelliSwitch controls)` |
| `model` | localName | `218542A01` |
| `company_id` | hard-coded | `0x0875` |
| `payload_hex` | mfg bytes 2..25 | manufacturer payload (CID stripped) |
| `rotating_field_note` | hard-coded | notes the opaque varying field |
| `attribution` | hard-coded | `id_only` |

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
- Captures: `research/nearsight_export 7.json` (~6 sightings, 1 device, localName `218542A01`, three rotating-field variants).
