# Dexcom DXCM** Plugin (G7 / ONE+ / Stelo)

## Overview

Dexcom's third-generation continuous-glucose-monitor family — the **G7**, the
international/budget **Dexcom ONE+**, and the OTC **Stelo** (launched 2024 in
the US for non-diabetic, pre-diabetic, and Type 2 non-insulin users) — share a
single BLE broadcast envelope. All three are built around the same disposable
single-piece sensor-plus-transmitter form factor and the same advertising
firmware, and they all surface as `DXCM<XX>` in CoreBluetooth scans, where
`<XX>` is a per-sensor two-character slot.

The disambiguation between G7, ONE+, and Stelo is **not** present in the
advertisement — it happens after the user enters the four-digit pairing code
printed on the sensor applicator inside the Dexcom app (or xDrip+). Per xDrip+
support docs, "DXCM**, DX01**, or DX02**" all reach the same Dexcom GATT
backend; the model split is server-side / app-side.

We surface the device as `Dexcom (G7/ONE+/Stelo)` with explicit uncertainty
in the model field. This avoids the failure mode of confidently telling the
user "this is a Stelo" when it might be a G7 worn by a Type 1 diabetic.

A separate parser (`DexcomCGMParser`) covers the older G6 ("Dexcom8G"-style
local names) and the legacy 128-bit GAP UUID; the DXCM family is disjoint
from those anchors, so we ship `DexcomSteloParser` rather than extending the
old one.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Company ID | `0x00D0` (Dexcom, Inc. — SIG-assigned) |
| Service UUID | `0xFEBC` (Dexcom, Inc. — SIG-assigned, 16-bit short form) |
| Local name | `DXCM<XX>` where `<XX>` is the per-sensor 2-char serial slot |

We match if **either**:
- The local name has the `DXCM` prefix, OR
- Both the Dexcom CID `0x00D0` AND the FEBC service UUID are present.

Requiring both anchors when the name is missing avoids false positives from
isolated FEBC sightings or stray `0x00D0` advertisements from older Dexcom
hardware that happens not to carry the FEBC short UUID.

### Manufacturer Data Layout (6 bytes)

```
Bytes 0..1   : d0 00                   ← LE Dexcom company ID
Bytes 2..4   : XX XX XX                ← 3-byte variable payload (rolling
                                         counter / wear-time / battery
                                         frame — not decoded)
Byte  5      : 04                      ← constant across captures
                                         (presumed protocol version or
                                         frame-type tag)
```

Observed samples from `research/adwatch_export 6.json`:

| Local name | Manufacturer hex | Variable payload | Constant tail |
|---|---|---|---|
| `DXCMKC` | `d0003e981204` | `3e 98 12` | `04` |
| `DXCMRx` | `d000661b0204` | `66 1b 02` | `04` |

We surface the four bytes after the company ID as `payload_hex` so future
captures can be diffed against these baselines without re-parsing.

### Local Name Format

`DXCM` (4 ASCII chars) + 2 ASCII chars per-sensor slot (e.g. `KC`, `Rx`,
`AB`). The 2-char slot is **not** the four-digit pairing code from the
applicator — it appears to be a Bluetooth-layer rotating identifier so
that multiple sensors used in series by the same person each get a
distinct entry in iOS/Android's "Other Devices" list. We expose it as
`metadata["serial_slot"]` and key the stable identifier on the full
local name (`dexcom_dxcm:DXCMKC`) so the same sensor across multiple
sightings collapses to one logical device.

### Stable Key

`dexcom_dxcm:<localName>` (e.g. `dexcom_dxcm:DXCMKC`). When the
advertisement carries no local name and only matches via CID+FEBC, we
fall back to a MAC-hash identifier so we still log the sighting.

## Detection Significance

- **Medical-device adjacency indicator.** A `DXCMxx` sighting in a residential
  scan tells us at least one occupant is wearing a Dexcom CGM. Pre-2024 that
  was a near-certain Type 1 or insulin-dependent Type 2 diabetes signal; with
  Stelo's OTC launch the signal now also covers metabolic-health hobbyists,
  athletes, and pre-diabetic monitoring. We deliberately do not infer disease
  state from the advertisement.
- **Public-health monitoring use.** Aggregate counts of DXCM-prefixed
  broadcasts in a region track CGM adoption — a meaningful proxy for OTC
  health-tech penetration post-Stelo.
- **Sensor cadence.** Each sensor lasts ~10–15 days; a household with one
  CGM user will rotate through a new `DXCM<XX>` slot roughly every two
  weeks. Distinct serial slots reaching us in quick succession from the
  same MAC neighborhood likely indicate a single user transitioning
  sensors, not multiple users.

## What We Cannot Parse from Advertisements

- **Live glucose readings.** The CGM channel is encrypted and bound to a
  pairing key derived from the applicator code. Dexcom requires SDK
  authentication for partner apps. Reverse-engineered decoders exist
  (xDrip+, Loop, OpenAPS) but they all proceed via GATT subscriptions
  post-pairing, not from passive advertisement data.
- **Battery / wear-time.** Likely encoded in the variable 3-byte region
  but not yet decoded. A controlled capture across a sensor's full
  lifecycle would let us correlate.
- **Product line discrimination (G7 vs ONE+ vs Stelo).** Not exposed in
  the advertisement — see Overview.
- **Pairing code.** The 4-digit code is printed on the applicator and
  never broadcast.

## References

- [Dexcom Stelo product page](https://www.stelo.com/) — OTC CGM, US launch 2024.
- [Dexcom G7 product page](https://www.dexcom.com/en-us/g7-cgm-system)
- [xDrip+ — G7, ONE+, or Stelo support](https://navid200.github.io/xDrip/docs/Dexcom/G7.html) — documents the `DXCM**` / `DX01**` / `DX02**` broadcast naming and the shared GATT backend.
- [xDrip+ Stelo discussion (NightscoutFoundation/xDrip #3645)](https://github.com/NightscoutFoundation/xDrip/discussions/3645)
- [xDrip+ Stelo calibration discussion (#3954)](https://github.com/NightscoutFoundation/xDrip/discussions/3954)
- [AndroidAPS — Dexcom G7 compatibility](https://androidaps.readthedocs.io/en/latest/CompatibleCgms/DexcomG7.html)
- [Dexcom — Remove old sensors from Bluetooth list](https://www.dexcom.com/en-us/faqs/remove-old-sensors-from-bluetooth-list) — confirms `DXCM`-prefixed name pattern for G7-family sensors.
- [Bluetooth SIG company identifiers](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — confirms `0x00D0` = Dexcom, Inc.
- [Bluetooth SIG member services UUIDs](https://www.bluetooth.com/specifications/assigned-numbers/) — confirms `0xFEBC` is allocated to Dexcom.
