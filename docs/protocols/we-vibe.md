# We-Vibe (Standard Innovation) Devices

## Overview

We-Vibe intimate devices (Sync, Chorus, Jive, Moxie, …; app
`standardinnovation-weconnect` in apk-ble-hunting) advertise continuously while
powered. The app recognises a device when its advertised UUID list contains one
of two 16-bit service UUIDs (`l/k/a/a/n/b.java:8-10`). The local name is the
bare product model.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0x1900` (written as `4c421900-0000-1000-8000-00805f9b34fb`) | Primary discriminator |
| Service UUID | `0xBB03` (`0000bb03-0000-1000-8000-00805f9b34fb`) | Primary discriminator |
| Local name | product model: `Chorus`, `Sync`, `Jive`, `Moxie`, `Melt`, `Vector`, `Wand`, `Ditto`, `Pivot` | No vendor prefix |
| Company ID | — | Not parsed by the app |

> Note: the report expands `0x1900` as `4c421900-0000-1000-8000-00805f9b34fb`.
> That is **not** the SIG base expansion of `0x1900` (which would be
> `00001900-…`); `4c421900-…` is a 128-bit UUID whose 16-bit-position bytes are
> `1900`. A scanner should match the full `4c421900-0000-1000-8000-00805f9b34fb`
> as given, and verify on a live capture which form is advertised.

## What We Can Parse from Advertisements

Brand + exact model (from the name).

## What Requires GATT

Motor control and all state. (Historic app-side exfiltration of intensity /
temperature was remediated after the $3.75M privacy settlement — not an
advertisement issue.)

## Identity Hashing

`SHA256("we-vibe:{mac}:{local_name}")[:16]` — the name is a model, not per-unit.

## Detection Significance

**High privacy sensitivity.** UUID + model name unambiguously mark a We-Vibe
intimate device.

## adwatch Status

No plugin. Future match: service UUID `4c421900-0000-1000-8000-00805f9b34fb` or
`bb03`, name as metadata. See also [lovense.md](lovense.md),
[satisfyer.md](satisfyer.md), [svakom.md](svakom.md),
[magic-motion.md](magic-motion.md).

## References

- apk-ble-hunting `reports/standardinnovation-weconnect_passive.md`
- Code cited by the report: `l/k/a/a/n/b.java:8-10`
