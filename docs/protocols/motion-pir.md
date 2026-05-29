# MOTION_xxxx wireless PIR sensor

## Overview

Generic / white-label wireless PIR motion sensor family that advertises a 10-byte BLE manufacturer-data frame and a `MOTION_<4 hex>` local name. The Bluetooth SIG company ID slot is occupied by `0x0502` (registered to *Imagination Marketing SARL*), but the actual hardware has nothing to do with Imagination — the firmware reuses the CID for an unrelated PIR product, almost certainly a cheap Chinese OEM board re-sold under several brand names. Vendor-level identification is unconfirmed; we surface the bytes verbatim.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0502` | LE `02 05` — SIG yaml entry is *Imagination Marketing SARL* but the captured devices are not Imagination products |
| Local name | `MOTION_<4 hex>` | e.g. `MOTION_0476`, `MOTION_FD0A`, `MOTION_F5C7`. The 4-hex suffix is the same `unit_id` carried in the manufacturer-data payload |
| Address type | Random | Each capture rotated the BLE address |

### Manufacturer Data Layout (10 bytes total)

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| 0 | 2 | Company ID | `02 05` (LE → 0x0502) |
| 2 | 2 | Frame version | Always `00 00` in captured frames; non-zero rejected as unknown format |
| 4 | 4 | Install token | Opaque per-device identifier; stable across observations of the same unit |
| 8 | 2 | Unit ID | Per-device serial; hex equals the local-name suffix |

### Captured examples

| Local name | Manufacturer data (hex) | install_token | unit_id |
|------------|-------------------------|---------------|---------|
| `MOTION_0476` | `020500004a477f540476` | `4a477f54` | `0476` |
| `MOTION_FD0A` | `020500004a47608ffd0a` | `4a47608f` | `fd0a` |
| `MOTION_F5C7` | `020500007b988fbbf5c7` | `7b988fbb` | `f5c7` |

The first two units share the install-token prefix `4a 47 ...`, suggesting either a batch-level salt or a regional factory marker; we don't unpack it further.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor presence | CID + payload-length anchor | Identifies the device family |
| Install token | bytes [4..7] | Stable per-unit ID; used for the `identifier_hash` so MAC rotation does not split a device |
| Unit ID | bytes [8..9] | Matches the local-name suffix |
| `unit_id_matches_name` | sanity flag | `true` when the local-name suffix equals `unit_id` (hex) |

### What We Cannot Parse from Advertisements

- Motion-event state (PIR triggered / clear)
- Battery level
- Tamper / low-battery flags
- Specific brand / SKU
- Sensitivity, dwell time, or any configuration

Live state and configuration would require GATT enumeration on a sample unit — none has been reverse-engineered publicly.

## Detection Significance

- Identifies a presence-monitoring device in the environment (privacy-relevant signal in someone's home or workplace).
- Stable per-unit `identifier_hash` survives MAC rotation, which is important for correlating recurrent sightings across days.
- CID-vs-vendor mismatch is a hint that the broadcaster is hobbyist or low-end OEM firmware — useful context for the user.

## References

- Bluetooth SIG company_identifiers.yaml — `0x0502 = Imagination Marketing SARL` (vendor mismatch noted above).
- Captures: `research/adwatch_export 13.json`.
