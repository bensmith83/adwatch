# Generic 6-digit / MAC-suffix BLE asset tag

## Overview

Vendor-unconfirmed BLE asset-tag family identified by a single 128-bit vendor service UUID. Captured 17 times across 7 export sessions (every recent export has at least one sighting), making it one of the most consistently recurring uncovered devices in the corpus. The advertisement is service-UUID-only — no manufacturer data, no service data — and the local name encodes a per-site code + MAC suffix.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `4772911E-D07C-4617-8241-F4D10948D6AE` | Vendor-allocated; no SIG entry |
| Manufacturer data | _(absent)_ | Privacy-aware bare beacon |
| Service data | _(absent)_ | |
| Address type | Random | Rotates independently from the in-name MAC suffix |

### Local name convention

`<6 digits>_<MAC suffix>` where:

- The 6-digit prefix is a site / fleet / account code burned at provisioning. It recurs across multiple captures with the same value (`113685`, `113360`, `110092` observed).
- The suffix is either the full 12-hex MAC (e.g. `9C139E556148`) or a shortened 4-hex tail (e.g. `8AD4`). The full form is the persistent printed MAC; the short form is the broadcast hint.

| Captured names |
|----------------|
| `113685_9C139E556148` |
| `113360_30EDA08F0820` |
| `110092_8AD4` |

### What We Can Parse

| Field | Source | Notes |
|-------|--------|-------|
| `site_code` | localname `[0..5]` | 6-digit fleet/site code |
| `mac_suffix` | localname `[7..]` | Persistent device identifier |
| `suffix_kind` | derived | `full_mac` (12 hex) vs `short` (4 hex) |

### What We Cannot Parse

- Vendor / brand (pending physical-device confirmation by a user)
- Battery, motion, temperature, or any sensor state
- Firmware version

## Detection significance

- High cross-session recurrence (7/12 export files) means this is a real, recurring environmental device — worth surfacing even if the vendor is unknown.
- The `site_code` provides a useful grouping key for users who see many of these (likely an enterprise fleet — building access, retail, logistics).

## References

- Captures: `research/adwatch_export.json`, `research/adwatch_export 3/4/6/8/9/12/13.json`.
- The vendor UUID has no public reverse-engineering writeup as of capture date.
