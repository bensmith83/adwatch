# Magic Motion (Vtrump) Devices

## Overview

Magic Motion intimate devices (Flamingo, Smart Mini Vibe family; app
`vt-magicmotion` in apk-ble-hunting, Vtrump VTBLE SDK) advertise continuously
while powered. The app discovers by device name + an RSSI floor
(`VTDeviceManager.java:104,182`) and confirms by a VT custom service UUID after
connecting. For a passive scanner the **VT 128-bit service-UUID families** are
the strongest fingerprint (if advertised).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `78667579-b465-4ef3-a5c6-e8d9bc6c3f8f` | Current generation |
| Service UUID | `993c5ffa-1448-4981-9e03-4ed17dd81083` | VT family |
| Service UUID | `ca15a4b3-c94d-ebd8-7502-094c80a0b54c` | VT family |
| Service UUID | `f433bd80-75b8-11e2-97d9-0002a5d5c51b` | Legacy family |
| Service UUID | `f000ffc0-0451-4000-b000-000000000000` (TI OAD) | Device in OAD firmware-update mode (legacy TI CC254x) |
| Local name | model-specific | No uniform `MM-` prefix confirmed (the `"MagicMotion"` string in the app is music metadata) |
| Company ID | — | Not parsed |

The report's text expresses the TI OAD UUID as `f000ffc0-0451-4000-b000-0`; the
full form above is the standard TI OAD service UUID.

## What We Can Parse from Advertisements

Presence/brand; OAD-mode flag if the TI service appears.

## What Requires GATT

Motor control, battery (`180f/2a19`). Remote control rides the RongCloud IM
cloud bridge.

## Identity Hashing

`SHA256("magic-motion:{mac}:{local_name}")[:16]`.

## Detection Significance

**High privacy sensitivity.** This family is tied to **CVE-2020-12731** (no BLE
authentication), so passive detection escalates directly to unauthenticated
control.

## adwatch Status

No plugin. Future match: any of the VT service UUIDs above. See also
[lovense.md](lovense.md), [we-vibe.md](we-vibe.md), [satisfyer.md](satisfyer.md),
[svakom.md](svakom.md).

## References

- apk-ble-hunting `reports/vt-magicmotion_passive.md`
- Code cited by the report: `VTDeviceManager.java:104,182`
