# Vaultek (smart gun safes)

## Overview

Vaultek ships consumer biometric pistol safes (VT, MX, RS, LifePod
product lines) that pair with the Vaultek companion app over BLE for
remote status / unlock / audit-log retrieval. The fingerprint we
parse was characterized by Two Six Labs' "BlueSteal" research on the
VT20i (CVE-2017-17435 / CVE-2017-17436) and appears to be reused
across the line.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | *(none)* | Vaultek has no SIG-assigned company ID. |
| Service UUID | `0e2d8b6d-8b5e-91d5-b370-6f0a1bc57ab3` | Vendor-allocated 128-bit. Random; collision with another vendor is essentially zero. |
| GAP local name | contains `VAULTEK` (case-insensitive) | Often with model suffix, e.g. `VAULTEK-VT20i`. |

Either signal is independently strong. The parser claims a match
on a single signal; we don't require both, because the UUID is
random enough on its own and "vaultek" is not an English word.

## Model Suffix

When the GAP name carries a `VAULTEK-<model>` or `VAULTEK <model>`
suffix, we surface `<model>` as `metadata["model"]`. Validated as
≤16 alnum chars to avoid pulling garbage into the field.

Observed models in the wild include VT20i, VT10i, MX, MXi, RS500i,
RS800i, LifePod. We don't distinguish device subclass (handgun
safe vs. rifle safe vs. document safe) from the advertisement
because the suffix is opaque.

## Identity Hashing

```
stable_key      = "vaultek:" + mac_address
identifier_hash = SHA256(stable_key)[:16]
```

Vaultek devices use BLE public addresses (no rotation observed),
so the MAC is stable across sessions and is the right key for
cross-session identity.

## What We Can Parse Passively

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | UUID or name | "Vaultek" (high confidence). |
| Model | local-name suffix | When present. |
| Per-unit identity | MAC | Stable; public address. |

## What Requires GATT (and security note)

- Safe state (locked / unlocked, last-open audit log, battery)
  exposed via writable / notifiable characteristics on the same
  proprietary service.
- The Two Six Labs research demonstrated that the older VT20i
  firmware exposes the unlock command *without authentication*
  ("BlueSteal"). Vaultek shipped a firmware update in 2018; we
  don't probe state and can't tell from a passive scan whether
  the safe is patched.

## Threat Model Notes

A passive observer can detect that a Vaultek safe is present and
unique-identify it by MAC across sessions. The advertisement does
not include safe-state, contents, or battery level — those require
a connection to the GATT control plane. The MAC is a strong
identifier for "the same safe over time" though, so this is a
location-privacy concern if the safe travels with the owner (the
RS line is portable).

## References

- Two Six Labs, "BlueSteal: Popping GATT Safes" (2017-12)
  https://twosixtech.com/blog/bluesteal-popping-gatt-safes/
- CVE-2017-17435 — Vaultek VT20i unauthenticated unlock
- CVE-2017-17436 — Vaultek VT20i plaintext PIN transmission
- Vaultek product line: https://vaulteksafe.com/
