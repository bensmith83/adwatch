# Unknown `3E1D50CD-…` BLE Device Plugin

## Overview

A family of BLE devices observed in a 2026-05-19 scan sharing the custom 128-bit service UUID `3E1D50CD-7E3E-427D-8E1C-B78AA87FE624` and a single-character local name `"4"`. **The vendor could not be identified** from public sources, but the UUID + name combination is unique and specific enough to fingerprint the family reliably.

This was the *most-frequent unparsed device family* in the export (5 distinct device identifiers, all advertising the same UUID + single-digit name; 180 sightings in `nearsight_export 7`), which makes it valuable to surface even without semantic protocol knowledge — it lets us count, group, and eventually annotate the family once a labelled specimen is observed.

## Investigated leads (2026-06-29) — still UNATTRIBUTED on purpose

Authenticated GitHub code search (which had failed in earlier sweeps) now
returns hits, but they are **contested and weak**, so we deliberately keep
this an honest unknown rather than assert a vendor:

- **Flock Safety ALPR camera — REFUTED.** The only source tying this UUID to
  Flock is a single unsourced 3★ hobby repo (`cyclonite69/shadowcheck-web`),
  whose "name `4` / 10-digit ⇒ Flock" rules are circular and generic. The
  *canonical* Flock-detection tooling (`colonelpanichacks/flock-you` 1135★,
  ryanohoro, `MaxwellDPS/Flock-You-Android`) keys on **company ID `0x09C8`
  (XUNTONG)** + OUI + `Penguin`/`FS Ext Battery` names and **never cites this
  UUID**. Our captures carry **no manufacturer data**, so they lack the
  XUNTONG ID that actually confirms a Flock Penguin — they fail the real
  validation test. Do **not** label this Flock.
- **Focal / Naim "Auracast" (Vervent Audio Group, CID `0x0BA4`) — TENTATIVE.**
  A single 0★ repo (`digimap2000/auracle_now_moved`) maps the UUID to
  Focal/Naim, and it is technically plausible (it lists this UUID beside the
  standard LE-Audio GATT services ASCS/BASS/PAC/BAP; Focal & Naim are
  Vervent brands and Auracast-capable). Single-source and unconfirmed.

Per project policy (no named-vendor claim at moderate confidence; costly
false positives — cf. the retracted "TraceX" attribution), the parser stays
`unknown_3e1d50cd`. Revisit if a frame appears with XUNTONG `0x09C8` mfr data
(⇒ Flock) or Vervent `0x0BA4` mfr data / a `Mu-so`-style name (⇒ Focal/Naim).

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Service UUID (128-bit, custom) | `3E1D50CD-7E3E-427D-8E1C-B78AA87FE624` |
| Local name | `"4"` (literal single digit; observed identically across all 5 emitters) |
| Manufacturer data | none |
| Service data | none |
| Address type | random (rotates) |

### Why the single-digit name?

The 31-byte BLE advertisement PDU has limited room when a 128-bit service UUID (16 bytes + framing) is included. A vendor that needs to broadcast a tag/zone/channel number alongside the UUID has very little space left — a single ASCII digit fits in 1 byte of name, which is consistent with this family's `"4"` being a per-deployment label rather than a hardware serial. We do **not** assume `"4"` is unique across deployments; multiple unrelated sites could each install a `"4"`-labelled device.

### Stable Key

Because the local name is non-unique and there is no in-payload identifier, the stable key falls back to MAC-scoped:

```
unknown_3e1d50cd:<mac>
```

This means a single physical device whose MAC rotates will produce multiple stable keys over time — an unavoidable consequence of the family having no payload-side identifier.

## Detection Significance

- **High-specificity match.** A 128-bit custom UUID combined with a single-digit literal name is unique enough that the parser will not over-match.
- **Most-frequent unparsed family in the capture.** 5 distinct emitters in a single scan window suggests this device class is commonly deployed in at least one of the scan locations.
- **Hook for later identification.** Surfacing the family now lets us flag and count these devices; once a labelled specimen is identified, the parser can be upgraded to attach a real vendor name without changing the public contract.

## What We Cannot Parse

- **Vendor / model.** No manufacturer data, no service data, no public documentation. The parser is deliberately named `unknown_3e1d50cd` and does **not** invent a vendor.
- **Telemetry.** All payload is in the GATT characteristics behind the custom service — not in the advertisement.
- **A stable per-device identifier.** No payload-side serial exists; we fall back to MAC-scoping the stable key.

## References

- `research/adwatch_export 6.json` — 5 captured devices, all matching `localName == "4"` + service UUID `3E1D50CD-7E3E-427D-8E1C-B78AA87FE624`
- [NordicSemiconductor/bluetooth-numbers-database — `v1/service_uuids.json`](https://github.com/NordicSemiconductor/bluetooth-numbers-database/blob/master/v1/service_uuids.json) — checked 2026-05-20; UUID not present
- GitHub code search for `3E1D50CD-7E3E-427D-8E1C-B78AA87FE624` — no public results as of 2026-05-20; by 2026-06-29 authenticated `gh search code` returns 15 lines / 5 repos (see "Investigated leads" above — contested Flock vs. Focal/Naim, neither conclusive)
- Captures: `research/nearsight_export 7.json` (180 sightings, 2026-06-28)
