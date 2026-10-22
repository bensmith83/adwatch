# Omi / Friend AI Pendant

## Overview

**Omi** (Based Hardware; legacy "Friend" branding; package `com.friend.ios`)
is an open-source AI audio pendant. The app is Flutter: the Java layer is a
generic GATT bridge, while scan-filter UUIDs and framing are supplied from Dart
(`libapp.so`, deferred). Two passive facts are recoverable from Java:

1. **Discovery is by 128-bit service-UUID scan filter** (value Dart-supplied;
   primary audio service **inferred** as `19B10000-e8f2-537e-4f6c-d104768a1214`,
   MEDIUM confidence, from the OSS `BasedHardware/omi` firmware).
2. A **display-name fallback** recognises a third-party **NotePin** recorder by
   manufacturer data under CID `0x005D` with payload prefix `04 56 CF 00` —
   this is the PLAUD format, see [plaud.md](plaud.md). It is **not** the Omi
   pendant's own advert.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID (128-bit) | `19B10000-e8f2-537e-4f6c-d104768a1214` | **Inferred** (MEDIUM). All Omi UUIDs share the `…-e8f2-537e-4f6c-d104768a1214` base; the `19b10001` audio-notify char under it is hardcoded in Java (`OmiBleForegroundService.java:693`). Confirm the advertised literal from `libapp.so` or a capture. |
| Local name | e.g. `Omi` / `Friend` | **Unverified** (OSS firmware), MEDIUM; no name filter in the app |
| Company ID | — | Omi pendant manufacturer data, if any, is Dart-side (deferred) |

Scan: `ScanFilter.setServiceUuid` per Dart-supplied UUID, LOW_LATENCY; empty list
→ unfiltered scan (`com/friend/ios/ble/d.java:2030-2052`).

### NotePin naming heuristic (third-party device)

`B6/A.java:10-42`: if the advert has no name and
`getManufacturerSpecificData(93)` is ≥ 4 bytes starting `04 56 CF 00`, the app
labels it `"NotePin"`. See the cross-reference added to [plaud.md](plaud.md).
The report reads `0xCF` as a "MessagePack UINT64 opcode"; under adwatch's
`plaud.py` decode it is more naturally a PLAUD version record
(`len=04`, `'V'`, version LE starting `CF 00`).

## What We Can Parse from Advertisements

Presence of an Omi pendant via its service UUID (pending confirmation).

## What Requires GATT

Audio stream (`19b10001` notify, bonded LE) and all device state. Deep privacy
story (always-on mic → STT → cloud) is connection/cloud-side.

## Identity Hashing

`SHA256("omi:{mac}")[:16]`; no in-advert identifier known.

## Detection Significance

An always-on-mic wearable discoverable by a static service UUID — correlatable
across sessions unless the firmware randomizes the address.

## adwatch Status

No plugin for the Omi pendant. A future plugin would match service UUID
`19b10000-e8f2-537e-4f6c-d104768a1214` once confirmed. NotePin adverts are
already handled by `src/adwatch/plugins/plaud.py` (CIDs `0x0059`/`0x005D`).

## References

- apk-ble-hunting `reports/friend-ios_passive.md` (and `reports/friend-ios.md`)
- Code cited by the report: `com/friend/ios/ble/d.java` (`:869`, `:2030-2052`),
  `B6/A.java:10-42`, `OmiBleForegroundService.java:693`
- OSS firmware: https://github.com/BasedHardware/omi
