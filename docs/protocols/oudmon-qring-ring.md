# Oudmon / QRing / COLMI White-Label Smart Rings

## Overview

The **Oudmon BLE SDK** (`com.oudmon.ble.*`) is the upstream SDK behind the
"Yawell / QRing / COLMI" white-label smart-ring fleet — COLMI R02/R03/R06 and the
many AliExpress clones. The companion app analysed is **QRing**
(`com.app.cq.ring`, UI namespace `com.qcwireless.smart`). Secondary SDKs in the
app: Realtek RealSil (SoC / OTA) and Jieli (classic-BT SPP on audio variants).

The passive surface is deliberately thin: **presence + advertised service UUID
`0xFEE7` + a model-code local name**. The app parses the scan record into a
`ScanRecord` object and then throws it away (every ring consumer of
`onParsedData` has an empty body). There is **no manufacturer data and no
service data** to decode; all biometrics and control are post-connect.

This is a distinct profile from the sibling CRRepa/MoYoung ring fleet
([crrepa-moyoung-ring.md](crrepa-moyoung-ring.md), service data `0xFDDA`/`0xFDD0`)
and the ZH "Berry-Ring" fleet ([zh-berry-ring.md](zh-berry-ring.md), service
data `0xFE78`).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID (16-bit) | `0xFEE7` (`0000fee7-0000-1000-8000-00805f9b34fb`) | Tencent Holdings Limited SIG member UUID, reused by this fleet. Used by the app as its **background** `ScanFilter` (`BluetoothScannerImplLollipop.java:82`). Not unique — also used by Tencent-SDK wearables (see [coros-watch.md](coros-watch.md), [wyze-watch.md](wyze-watch.md)). Report notes the `fee0` hint from earlier stages is wrong/absent. |
| Local name prefix (priority 1, model codes) | `T80` `T90` `T91` `T93` `T95` `TW68` `S9` `C60` `C66` `C67` `C68` `C80` `C86` `C88` `C96` `wxb_w4` | Yawell/COLMI model codes — the prefix **is** the model code (`BleScannerHelper.java:27`) |
| Local name prefix (priority 2) | `O_` / `o_` | Oudmon-family prefix (`BleScannerHelper.java:142`) |
| Local name prefix (priority 3) | `Q_` / `q_`, `R3L`, `QC` / `qc`, `Wa` | QRing / rebadge prefixes (`BleScannerHelper.java:151`, `DeviceBindViewModel.java:337`) |
| Local name prefix (runtime) | server-supplied | `getScanConfigFromServer` adds prefixes without an app update (`DeviceBindViewModel.java:333`) — treat the list as extensible |
| Company ID | — | No manufacturer data is read on the ring scan path (only the Realtek OTA scanner touches mfr/service data) |

Foreground scans are unfiltered (LOW_LATENCY) and match by name in the callback;
background scans filter on `0xFEE7` (LOW_POWER).

### Device name encoding

`<model-code prefix><device-specific suffix>`. Matching is `startsWith` only; no
serial, MAC or state is decoded from the name. The suffix is firmware-set and
not interpreted by the app.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Fleet membership | `0xFEE7` and/or name prefix | QRing/Oudmon/COLMI ring |
| Model code | name prefix | e.g. `C`-series codes indicate ECG-capable models (per report) |

## What Requires GATT

Everything else — HR / SpO2 / ECG / PPG / stress / sleep / battery and control —
travels over a Nordic-UART-variant channel (`6e40fff0` service, write
`6e400002`, notify `6e400003`) plus a Realtek `de5bf728` large-data/OTA service.
The report notes this channel is **unauthenticated** at the app layer.

## Identity Hashing

No in-advert serial. Suggested: `SHA256("qring:{mac}:{local_name}")[:16]`.
Cross-session stability depends on whether the ring uses a static address
(not determinable from the app).

## Detection Significance

- The name prefix discloses the exact hardware model (and feature set) before
  any connection.
- `0xFEE7` brands the advertiser as a QRing-fleet ring even if the name is
  customised — but `0xFEE7` alone must not be attributed to this fleet (shared
  Tencent UUID). Require a name prefix match, or treat `0xFEE7`-only as a weak
  hint.
- Because the post-connect channel has no app-layer auth, passive discovery is
  the first step of a live-PHI harvesting chain for anyone in range.

## adwatch Status

No plugin matches this fleet. A future plugin would match name prefixes (the
list above) with `0xFEE7` as corroboration; nothing to decode beyond model code.

## References

- apk-ble-hunting `reports/app-cq-ring_passive.md` (and `reports/app-cq-ring.md`
  for the GATT catalog)
- Code cited by the report: `com.oudmon.ble.base.scan.BluetoothScannerImplLollipop`
  (`:74-88`), `BleScannerHelper.filterResult` (`:138-160`, prefix list `:27`),
  `com.qcwireless.smart.ui.device.connect.DeviceBindViewModel` (`:333`, `:337`)
