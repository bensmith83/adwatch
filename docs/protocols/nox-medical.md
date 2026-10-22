# Nox Medical Sleep-Study Recorders (A1 / A1s / C1 / T3s)

## Overview

Nox Medical (Iceland) makes polysomnography / home sleep test recorders —
A1, A1s, the C1 console, and the older T3s — plus a bundled Nonin 3150
oximeter accessory, driven by the **Noxturnal App**
(`com.noxmedical.mobile`). The system is **dual-transport**:

- **BLE:** A1 / A1s / C1 — connectable adverts, name-encoded, no telemetry.
- **BT Classic:** T3s (RFCOMM) and Nonin 3150 (SPP) — invisible to a BLE
  passive scanner (BR/EDR inquiry only).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | *(not used by app)* | SIG registry (`src/adwatch/_bt_company_ids.py`) lists `0x03FB` (1019) = Nox Medical, but the report finds **no** manufacturer-data parsing in the app; whether recorders emit `0x03FB` MSD is unverified. |
| Service UUID | *(not advertised as discovery key)* | Vendor GATT service `f3641400-00b0-4240-ba50-05ca45bf8abc` is used post-connect. |
| Local name | `<MODEL>_<tail>` with MODEL ∈ {`A1`, `A1S`, `C1`} on BLE (`T3` is Classic) | Split on `_`; ≥2 parts required; first token selects device type. |

The app runs an **unfiltered** LE scan in parallel with Classic
`startDiscovery()` and classifies by name.

Device-type enum: `A1ViaC1`, `Console`, `A1`, `T3`, `A1S`.

`fcdf02ff-…` and `65c4e3bd-…` in the app are PSG RecordingID/TemplateID
strings, **not** BLE UUIDs.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor + model | name first token | `A1`, `A1S`, `C1` |
| Candidate unit ID | name second token | Format not pinned; serial vs internal ID **unproven** |

## What Requires GATT Connection

- The full PSG montage (EEG/EOG/EMG/ECG/respiratory/SpO2) via notify on
  `f3641402` — only after **bonding** (`onServicesDiscovered` branches on
  `BONDED`).

## Identity Hashing

```
identifier = SHA256("nox:" + name_tail)[:16]   # if the tail proves stable
identifier = SHA256("nox:" + mac)[:16]         # fallback
```

## Detection Significance

- An `A1_…` / `A1S_…` / `C1_…` name reveals someone is undergoing a sleep
  study (PSG/HST) — medical context. Stage 5b audit keeps this at
  **LOW/INFO** (inherent to the GAP name; connectable, not a continuous
  beacon).
- Serial-in-name tracking is **downgraded → unproven** (the classifier only
  uses `parts[0]`).
- Short tokens like `A1_` / `C1_` may collide with unrelated products —
  treat as low-confidence without corroboration.

## adwatch Status

No plugin. A future plugin would match local names `^(A1|A1S|C1)_` and
expose the model + hashed tail; optionally check for CID `0x03FB` MSD if a
live capture shows one.

## References

- apk-ble-hunting `reports/noxmedical-mobile_passive.md` (Stage 4: `reports/noxmedical-mobile.md`; audit `reports/_audit_batch27.md` §H)
- App code cited: `BluetoothDiscoveryService.java:333,343,354` (dual scan), `F0/x.java:202-207` (name split), `K0/r.java:44-56` (type enum), `DeviceLeCommService.java:378-385,511,558-563`, `E0/a.java:184`
