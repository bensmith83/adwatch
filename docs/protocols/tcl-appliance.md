# TCL King appliance (embedded-MAC FFC0 beacon)

## Overview

**TCL King Electrical Appliances (Huizhou) Co., Ltd** is a TCL subsidiary
that makes TVs, soundbars, and home appliances. A device in this family
advertises a fixed 10-byte manufacturer-data payload under a non-SIG
**vanity company ID `0x1006`**, two reserved/unknown bytes, and then the
**device's own embedded 6-byte MAC**. The first three bytes of that
embedded MAC are the IEEE OUI **`2C:E0:32`**, which the IEEE OUI registry
assigns to TCL King — that is the decisive attribution signal.

This is **attribution-only**: the parser identifies the vendor/unit, but
the payload contains **no decodable telemetry or device state**.

This was the most-seen unparsed device in the capture set
(`research/nearsight_export 7.json`, 164 sightings).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Manufacturer data | `06 10 00 00 <embedded MAC[6]>` (exactly 10 bytes) | Vanity CID 0x1006 + 2 reserved bytes + embedded MAC |
| Company ID | `0x1006` | **Non-SIG vanity CID** — not registered with the Bluetooth SIG |
| Service UUIDs | `["FFC0"]` | Generic/shared 16-bit UUID; recorded, **not** gated on |
| Local name | (none) | Not present in captures |
| Address type | `random` | Rotates on-air |

The match requires the vanity CID, the exact 10-byte length, the
`06 10 00 00` prefix, **and** an embedded OUI in the known TCL set. If the
embedded OUI is not a known TCL OUI, the parser returns nil — it does not
claim TCL for an arbitrary embedded MAC.

### Non-SIG CID + generic UUID caveat

`0x1006` is **not** a Bluetooth-SIG-assigned company identifier; it is a
vanity value embedded by the firmware, so it is not distinctive on its
own and collides freely with anything else that picks the same value.
Likewise `FFC0` is a generic/shared 16-bit service UUID used by many
unrelated products. Neither is gated on — the **embedded-MAC OUI** is the
only attribution signal.

### Manufacturer-data layout (exactly 10 bytes)

| Bytes | Value | Meaning |
|---|---|---|
| 0..1 | `06 10` | Vanity company ID 0x1006 (LE), non-SIG |
| 2..3 | `00 00` | Reserved / **unknown** |
| 4..6 | `2C E0 32` | Embedded-MAC OUI (IEEE → TCL King) |
| 7..9 | `XX XX XX` | Embedded-MAC device suffix |

Worked example: `061000002ce032c81ed2` → CID `0x1006`, reserved `0000`,
embedded MAC `2C:E0:32:C8:1E:D2` (OUI `2C:E0:32`).

### What we can surface

| Field | Source | Notes |
|---|---|---|
| `vendor` | hard-coded | `TCL King Electrical Appliances` |
| `embedded_mac` | mfg bytes 4..9 | colon-formatted, uppercase |
| `oui` | mfg bytes 4..6 | colon-formatted, uppercase |
| `company_id` | mfg bytes 0..1 | `0x1006` (non-SIG vanity) |
| `sig_id_status` | hard-coded | `non_sig_vanity` |
| `match` | hard-coded | `embedded_mac_oui` |
| `service_uuid` | serviceUUIDs | `ffc0` if advertised |

### What we cannot surface

- Any device state, telemetry, or product model — the payload carries no
  decodable fields beyond the embedded MAC.
- The meaning of the 2 reserved bytes (`00 00` in every observed frame) is
  **unknown**.
- Product type within the TCL King catalog (TV vs. soundbar vs.
  appliance) — not encoded in the advertisement.

## Stable identity

The embedded MAC is the per-unit stable identifier — it survives the
random-address rotation the radio uses on-air:

```
stable_key = tcl_appliance:<embedded_mac>   (e.g. tcl_appliance:2C:E0:32:C8:1E:D2)
identifier = SHA256(stable_key)[:16]
```

## Detection significance

- Identifies a TCL King home appliance / AV device family that would
  otherwise sit unparsed despite high sighting counts.
- The OUI gate prevents over-claiming: the vanity CID `0x1006` and the
  generic `FFC0` service UUID are shared/non-distinctive, so attribution
  rests solely on the IEEE-verified embedded-MAC OUI.
- Extensible: more TCL OUIs can be added to the static set as they are
  verified against the IEEE registry.

## References

- [IEEE OUI registry CSV](https://standards-oui.ieee.org/oui/oui.csv) — `2C:E0:32` → TCL King Electrical Appliances (Huizhou) Co., Ltd
- [Bluetooth SIG company_identifiers.yaml](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — `0x1006` is **not** present (non-SIG vanity CID)
- Captures: `research/nearsight_export 7.json` (164 sightings — most-seen unparsed device).
