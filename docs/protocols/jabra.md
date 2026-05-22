# Jabra (GN Audio) Plugin

## Overview

[Jabra](https://www.jabra.com/) is the consumer / enterprise audio brand owned by **GN Audio A/S**, a subsidiary of the Danish conglomerate **GN Store Nord A/S** (historically "GN Great Nordic", founded 1869 as a telegraph operator). GN runs three audio-adjacent business lines under separate Bluetooth SIG identities:

- **GN Audio / Jabra** — headsets, true-wireless earbuds, conference / video-bar hardware. The brand we cover here.
- **GN Hearing / ReSound** — prescription hearing aids (separate SIG allocations 0x0089, 0xFD20, 0xFD71, 0xFEFE — **not** routed by this parser).
- **BlueParrott** — trucker / over-the-road mono headsets, also a GN sub-brand.

Jabra product lines we recognise:

| Marketing line | Form factor | Examples |
|---|---|---|
| `Elite` | True-wireless earbuds (consumer) | `Elite 4`, `Elite 7 Pro`, `Elite 10` |
| `Elite Active` | Sport / fitness earbuds (sweat-rated) | `Elite Active 65t`, `Elite Active 75t`, `Elite Active` (gen-1) |
| `Talk` | Mono Bluetooth headset (single ear, call-only) | `Talk 5`, `Talk 25`, `Talk 65` |
| `Evolve` / `Evolve2` | UC / call-center over-ear and stereo headsets | `Evolve2 65`, `Evolve2 85`, `Evolve 75` |
| `Speak` | Conference speakerphone pucks | `Speak 510`, `Speak 750` |
| `PanaCast` | Video conferencing bars / cameras | `PanaCast 50`, `PanaCast 20` |

## BLE Advertisement Format

### Identification

The captured signature in `research/adwatch_export 9.json` (May 2026) is **name-only**:

```
localName="Jabra Elite Active"   mfg=nil   svc=nil   uuids=nil
```

One sighting, no manufacturer data, no service data. The local-name pattern is therefore the primary attribution anchor.

| Signal | Value |
|---|---|
| Manufacturer-data CID (optional) | `0x0067` — **GN Netcom A/S** (the GN subsidiary that historically shipped Jabra headsets; decimal 103, wire-LE bytes `67 00`). Surfaced in metadata as `sig_company_id` / `sig_vendor` when present. |
| 16-bit service UUID (optional) | `FEFF` — SIG-allocated to **GN Netcom**. Surfaced as `service_uuids` when present. |
| Local name | `^Jabra ` (case-sensitive, **with** the trailing space) |

The captured advertisement carried none of these optional signals, so they cannot be required — the local-name prefix alone gates attribution. The two SIG sibling allocations (`0xFEFE` GN ReSound, `0xFD20`/`0xFD71` GN Hearing) are **not** routed here because those product families are prescription hearing aids, not Jabra audio.

The user briefing speculated `0x0072` was "GN Audio A/S"; the SIG company-identifier list actually has `0x0072` registered to "ShangHai Super Smart Electronics Co. Ltd." — we therefore do not route 0x0072.

### Local Name Format

`Jabra <Model>` with a single ASCII space. Examples:

- `Jabra Elite Active` (captured)
- `Jabra Elite 4`
- `Jabra Elite 75t`
- `Jabra Elite Active 75t`
- `Jabra Talk 65`
- `Jabra Evolve2 65`
- `Jabra Speak 510`
- `Jabra PanaCast 50`

The trailing space in the prefix is load-bearing: we deliberately reject `JabraAudio` and other concatenated renames because the canonical Jabra format always carries the space. UI-side renames (e.g. a user changing the local name in Settings) will silently un-attribute the device.

### Product Family Map

We extract `model` as everything after `Jabra ` and infer `product_family` + `device_class` from the leading word(s):

| Model prefix | `product_family` | `device_class` |
|---|---|---|
| `Elite Active` | `Elite Active` | `earbuds` |
| `Elite` (without `Active`) | `Elite` | `earbuds` |
| `Talk` | `Talk` | `headset` |
| `Evolve` / `Evolve2` | `Evolve` | `headset` |
| `Speak` | `Speak` | `speakerphone` |
| `PanaCast` | `PanaCast` | `videobar` |
| (anything else) | _unset_ | `audio` |

`Elite Active` is checked before `Elite` so `Jabra Elite Active 75t` lands in the sport sub-family rather than the generic Elite line.

## Stable Key

`stableKey` is `nil`. The Jabra local name encodes only the marketing model — every `Jabra Elite Active 75t` in the world advertises the same string — and these earbuds use rotating random Bluetooth addresses, so the advertisement gives us neither a per-unit serial nor a stable BD_ADDR to anchor on. We surface the model in metadata for fleet/aggregate analysis but cannot claim per-device continuity from advertisements alone.

## Detection Significance

- **Workplace / call-center signal.** Jabra is one of the two dominant B2B Unified-Communications headset brands (alongside Poly/Plantronics). The Evolve / Evolve2 / Talk / Speak lines are standard-issue at call centers, contact centers, and corporate office deployments — a cluster of `Jabra Evolve2` sightings in a residential capture is a strong indicator of remote-work / WFH activity.
- **Sport sub-family proxies activity.** `Elite Active` carries an IP-rated sweat seal, marketed at runners / gym-goers — distinct from the consumer `Elite` line.
- **Conferencing infrastructure.** `PanaCast` and `Speak` advertise from fixed-install conference-room hardware; their appearance maps to office-occupancy patterns rather than mobile users.

## What We Cannot Parse from Advertisements

- **Battery / charge state** — Jabra Sound+ app reads these via GATT post-connect; they are not on the advertisement.
- **Active-noise-cancellation / passthrough mode** — configured over GATT.
- **Specific model variant where the local name is generic** (e.g. captured `Jabra Elite Active` does not tell us 65t vs 75t vs gen-1 — we set `model` = `Elite Active` exactly as advertised and leave the SKU disambiguation to higher layers).
- **Per-unit serial** — see Stable Key. Without GATT we have no per-device anchor for the rotating-MAC advertisements.

## References

- [Jabra corporate site (GN Audio brand)](https://www.jabra.com/)
- [GN Audio / GN Store Nord investor overview](https://www.jabra.com/about/investor)
- [Bluetooth SIG company identifiers (covers 0x0067 GN Netcom A/S)](https://www.bluetooth.com/specifications/assigned-numbers/company-identifiers/)
- [Bluetooth SIG 16-bit UUID assigned numbers (covers FEFF GN Netcom, FEFE GN ReSound, FD20/FD71 GN Hearing)](https://www.bluetooth.com/specifications/assigned-numbers/)
- [Jabra Elite Active 75t product page (sport sub-family)](https://www.jabra.com/bluetooth-headsets/jabra-elite-active-75t)
