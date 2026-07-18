# Car Connectivity Consortium (CCC) Digital Key

## Overview

The **CCC Digital Key** is the cross-industry standard that lets a phone (or
watch) act as a car key — unlock, lock, and start — over BLE + UWB + NFC. It
is governed by the **Car Connectivity Consortium** and adopted across brands
(BMW, Mercedes-Benz, Hyundai / Kia / Genesis, Audi, and more). Like
iBeacon / Eddystone, it is a **brand-agnostic standard**: the advertisement
identifies the *protocol*, **not the car brand**.

A CCC vehicle advertises the 16-bit service UUID **`FFF5`** (the Apple Nearby
Interaction / UWB ranging service, used by CCC for secure ranging) together
with service data under the 128-bit **"CCC intent" UUID**
`5810BBC0-B499-11E9-A2A3-2A2AE2DBCCE4`. This is distinct from brand-proprietary
digital keys such as the [Polestar / Volvo key](polestar-digital-key.md),
which use their own service UUIDs.

## Identification

| Signal | Value | Notes |
|---|---|---|
| Service data UUID | `5810BBC0-B499-11E9-A2A3-2A2AE2DBCCE4` | **the decisive anchor** ("CCCServiceDataIntent UUID") |
| Service UUID | `FFF5` | UWB / Apple-NIAP ranging service; co-advertised (corroborator, not the gate) |
| Manufacturer data | none | — |
| Address type | `random` | rotating; no stable per-vehicle identity in the advert |

> ⚠️ **Do not gate on `FFF5` alone** — it is the generic UWB/NIAP service used
> by many ranging-capable accessories. And **do not gate on the UUID-v1 node
> `2A2AE2DBCCE4`** — that node is a *generic, reused* UUID-v1 generator node
> (it also appears in unrelated projects: the Julia package ChainRulesCore, a
> Bosch eBike service, a GAN smart-cube, ad-tech SDKs, …). The decisive signal
> is the full `5810BBC0…` intent UUID in the service-data block.

### Why this = CCC Digital Key (attribution)

Two independent authoritative implementers use this exact advertisement
(authenticated GitHub code search):

- **Infineon** `mtb-example-btstack-freertos-le-ccc-adv` — titled *"Bluetooth
  LE Car Connectivity Consortium (CCC) Adv"* (AIROC CYW89829). Its design
  advertises service UUID `0xFFF5` and names `5810bbc0-b499-11e9-a2a3-
  2a2ae2dbcce4` literally **"CCCServiceDataIntent UUID"**, device name
  **"CCC_Vehicle"**.
- **Google AOSP** `bt-navi-tests` builds an advertising variant named
  **`LEGACY_CCCDK_SERVICE_UUID_AND_DATA`** (CCCDK = **CCC Digital Key**):
  `CompleteListOf16BitServiceUUIDs([FFF5])` + `ServiceData128BitUUID(
  5810bbc0-…, 01 00 02)`.

### Service-data byte map (`5810BBC0…` value)

Observed values: `01 00 ab`, `01 02 00` (reference designs also show `01 00 02`,
`01 00 00`).

| Bytes | Value | Meaning |
|---|---|---|
| 0 | `01` | format / intent indicator — **stable** across all samples |
| 1–2 | `XX XX` | opaque CCC state — **varies** (`00ab` / `0200` / `0002` / `0000`); exact meaning is in the member-only CCC Digital Key R3 spec |

The old "constant `01 02 00`" reading was wrong — bytes 1–2 vary per device /
over time, so they are not a stable identifier.

### What we can surface

| Field | Source | Notes |
|---|---|---|
| `standard` | hard-coded | `Car Connectivity Consortium (CCC) Digital Key` |
| `format_byte` | service-data byte 0 | `0x01` |
| `state_hex` | full service-data value | opaque |
| `state_field_hex` | bytes 1–2 | opaque CCC state |
| `uwb_ranging` | `FFF5` present | `yes` / `no` |
| `car_brand` | — | `not_derivable` (standard is brand-agnostic) |

### What we cannot surface

- The car make/model/owner — not encoded in the advert.
- Lock/unlock state, key identity, ranging distance — these are in the
  authenticated/UWB session, not the passive BLE advertisement.
- The silicon vendor — often Infineon AIROC, but not guaranteed.

## Parser scope (passive only)

Presence of a CCC Digital Key advertiser (i.e. a digital-key-equipped
vehicle, or a CCC dev kit/accessory) only.

## Stable identity

```
stable_key = ccc_digital_key:<mac>     (random address; session grouping only)
identifier = SHA256(stable_key)[:16]
```

No durable per-vehicle identity: the address rotates and the state bytes
change. Treat as presence/standard detection, not unit tracking.

## Detection significance

- Flags a **digital-key-equipped vehicle nearby** — a useful automotive
  context signal and a privacy note (the standard broadcasts continuously so
  the owner's phone can detect proximity).
- Complements brand-proprietary key parsers (e.g. Polestar/Volvo) with the
  cross-brand CCC standard.

## References

- [Car Connectivity Consortium — Digital Key](https://carconnectivity.org/digital-key/)
- [Infineon `mtb-example-btstack-freertos-le-ccc-adv`](https://github.com/Infineon/mtb-example-btstack-freertos-le-ccc-adv) — "CCC Adv", `0xFFF5`, "CCCServiceDataIntent UUID", "CCC_Vehicle"
- [Google AOSP `bt-navi-tests`](https://github.com/google/bt-navi-tests) — `LEGACY_CCCDK_SERVICE_UUID_AND_DATA`
- Captures: `research/nearsight_export 7.json` (2 vehicles, 56 sightings).
