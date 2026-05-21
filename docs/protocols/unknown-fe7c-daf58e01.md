# Unknown `0xFE7C` + `DAF58E01-…` BLE Device Plugin

## Overview

A single BLE device observed in a 2026-05-20 scan (Boston area, near Fenway
Park, ~18:52 UTC / 14:52 EDT) advertising two signals that no public source
attributes to a specific product family:

1. **Manufacturer data CID `0xFE7C`** — appears in the company-identifier slot
   of the manufacturer-data structure. This value IS a SIG-assigned 16-bit
   *Member Service UUID* (allocated to "Telit Wireless Solutions, formerly
   Stollmann E+V GmbH") but it is **NOT** a SIG-assigned Company Identifier.
   Using a member-UUID value as a CID is irregular.
2. **Custom 128-bit service UUID with prefix `DAF58E01`** — fully custom,
   not present in the SIG `member_uuids.yaml` / `service_uuids.yaml`, not
   present in `NordicSemiconductor/bluetooth-numbers-database`, and not
   surfacing in GitHub code search or Google.

The device emitted for ~12 seconds (9 sightings) at -83 to -92 dBm, then
disappeared — consistent with a mobile transmitter walking through the scan
area rather than a fixed installation.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Manufacturer data CID | `0xFE7C` (bytes `7c fe`, little-endian) |
| Manufacturer payload | `62 4b b7 3c 00 00` (6 bytes — 4 identifier-looking bytes + 2 reserved zeros) |
| Service UUID (128-bit, custom) | `DAF58E01-…` (CoreBluetooth exported only the 32-bit prefix in this capture) |
| Local name | absent |
| Service data | none |
| Address type | random |

### Captured sample

```
deviceIdentifier:     687734C5-58D5-92AA-92D5-DEFC86EDE177
manufacturerDataHex:  7cfe624bb73c0000
serviceUUIDsJSON:     ["DAF58E01"]
sightingCount:        9   (over ~12 s)
rssiMax/Min:          -83 / -92 dBm
firstSeen:            2026-05-20T18:52:31Z
lastSeen:             2026-05-20T18:52:43Z
addressType:          random
```

### Stable Key

```
unknown_fe7c_daf58e01:<mac>
```

MAC-scoped because (a) we have only a single observation and so cannot
identify which payload bytes (if any) are stable across MAC rotations, and
(b) the 4-byte mid-payload (`62 4b b7 3c`) could plausibly be either a
device serial OR a per-broadcast nonce — we lack the evidence to commit
either way.

## What We Figured Out

- **CID 0xFE7C is a SIG member-service-UUID, not a SIG CID.** The current
  `assigned_numbers/company_identifiers/company_identifiers.yaml` on the
  Bluetooth SIG public Bitbucket mirror tops out at `0x10C7`. CID 0xFE7C
  (65148 decimal) is far above that range and is **not** present in the
  company-identifiers file. It IS present in
  `assigned_numbers/uuids/member_uuids.yaml` as the 16-bit member service
  UUID assigned to "Telit Wireless Solutions (Formerly Stollmann E+V
  GmbH)". These are **different namespaces**, so a device using 0xFE7C as
  a CID is doing something irregular.

- **The "vanity-CID" framing applies.** Whether the vendor copy-pasted
  their member-UUID into the CID slot or someone unrelated chose 0xFE7C
  as a vanity squat, the manufacturer-data block is non-compliant. We
  surface this in the `vanity_cid_note` metadata so downstream consumers
  can see why we classify it under an "unknown" parser rather than under
  a Telit-vendor parser.

- **The disjointness rule.** Telit's *real* SIG-assigned Company
  Identifier is `0x008F`, and Telit also holds member-service-UUIDs
  `0xFE17` and `0xFEFB`. Our parser does **not** match any of these —
  they are legitimate Telit assignments used in their advertised channels
  and must continue to flow to whichever (future or current) parser
  handles legitimate Telit traffic.

- **The custom 128-bit service UUID does not match the SIG base.** The
  SIG base UUID for short-form 16-bit / 32-bit UUIDs is
  `XXXXXXXX-0000-1000-8000-00805F9B34FB`. The DAF58E01 prefix does not
  match any SIG-allocated short UUID — it is genuinely custom.

## What We Could NOT Figure Out

- **Vendor identity.** The 0xFE7C-as-CID signal is *suggestive* of a
  Telit-derived OEM SDK, but the absence of Telit-style protocol markers
  (e.g. BlueMod model strings) and the entirely unidentified
  `DAF58E01` custom UUID prevent confirmation. We deliberately leave the
  `vendor` metadata field unset.
- **Product family.** Could be ticketing hardware, employee badge, asset
  tag, concession terminal, sound-system controller, etc. The Fenway
  Park context is suggestive but uncorroborated; the device's short
  burst + weak RSSI is equally consistent with a pedestrian phone running
  a custom BLE app.
- **Payload semantics.** The 4-byte identifier-looking prefix
  `62 4b b7 3c` could be (a) a serial number, (b) a session nonce,
  (c) a truncated MAC, or (d) a checksum/tag of something else. Single
  observation, so we cannot distinguish.

## Dead-end searches (recorded so they aren't re-run)

- SIG `company_identifiers.yaml` — `0xFE7C` not present (highest entry
  `0x10C7` as of 2026-05-20).
- SIG `member_uuids.yaml` — `0xFE7C` IS present (Telit / Stollmann), but
  as a *service UUID*, not a company identifier.
- SIG `service_uuids.yaml` — `DAF58E01` not present.
- `NordicSemiconductor/bluetooth-numbers-database` `service_uuids.json` —
  `DAF58E01` not present.
- GitHub code search for `"DAF58E01"` — 27 hits, all substring-collision
  false positives (e.g. binary `.db` files, JPEG resource paths,
  unrelated openssh ChangeLog noise).
- GitHub code search for `"7cfe624bb73c"` and `"624bb73c"` — no
  bluetooth-relevant hits.
- GitHub code search for `"DAF58E01" Telit`, `"DAF58E01" Stollmann`,
  `"DAF58E01" BlueMod` — zero hits each.
- Web searches for `"0xFE7C" bluetooth`, `"DAF58E01" bluetooth`,
  `BlueMod custom UUID DAF5`, `Stollmann DAF5 SPP` — only generic
  documentation, no product match.
- Cross-export check: the payload `7cfe624bb73c` and the service UUID
  `DAF58E01` are present in *only* `adwatch_export 8.json` — not in any
  earlier export. This is a brand-new sighting, not a recurring device.

## Disjointness Rule (to Prevent Over-attribution)

This parser must NOT claim ads that are legitimate Telit / Stollmann
traffic:

- **Reject** advertisements with manufacturer-data CID `0x008F`
  (Telit's real SIG-assigned CID).
- **Reject** advertisements whose `serviceUUIDs` contain `"FE7C"` or
  `"0000fe7c-0000-1000-8000-00805f9b34fb"` (the proper 128-bit SIG-base
  encoding of FE7C as a service UUID) — that would be a Telit device
  using its member-UUID legitimately.
- **Match only** when 0xFE7C appears in the manufacturer-data CID slot
  (the squat case) AND/OR a serviceUUID has the custom 32-bit prefix
  `daf58e01` followed by `-` or end-of-string.

## Detection Significance

- **Distinctive fingerprint pair.** Either signal alone — the squatted
  CID or the custom UUID — is rare enough that the parser will not
  over-match.
- **Surface-only catalog entry.** We emit a recognizable beacon type
  (`unknown_fe7c_daf58e01`) with `device_class: unknown` so the device
  appears in lists / counts and can be correlated against future
  sightings.
- **Future upgrade path.** When (if) a labelled specimen or vendor SDK
  surfaces, the parser can be upgraded with a real vendor + product
  attribution without changing the public contract.

## References

- [Bluetooth SIG `assigned_numbers/uuids/member_uuids.yaml`](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — confirms 0xFE7C as Telit/Stollmann member UUID
- [Bluetooth SIG `assigned_numbers/company_identifiers/company_identifiers.yaml`](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — confirms 0xFE7C is NOT a SIG company identifier
- [NordicSemiconductor/bluetooth-numbers-database](https://github.com/NordicSemiconductor/bluetooth-numbers-database) — `DAF58E01` not present (verified 2026-05-20)
- `research/adwatch_export 8.json` — single sighting, lines around 20930-20942
