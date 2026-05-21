# Gimbal Plugin

## Overview

**Gimbal, Inc.** is a Bluetooth proximity-beacon vendor with an unusual SIG fingerprint: it owns *both* a company identifier and a 16-bit member service UUID in the canonical Bluetooth SIG registries.

| SIG registry | Code | Owner |
|---|---|---|
| `company_identifiers.yaml` | `0x008C` | Gimbal, Inc. |
| `member_uuids.yaml` | `0xFEFD` | Gimbal, Inc. |
| `member_uuids.yaml` | `0xFEFC` | Gimbal, Inc. |

The vendor history is well documented: Gimbal was spun out of Qualcomm in May 2014 (originally "Qualcomm Retail Solutions"), pivoted to a standalone proximity-and-context platform, and was acquired by The Mobile Majority in December 2016. Today the product line operates under Infillion, and the Gimbal Series 10 / 20 / 21 BLE beacons remain in active deployment for retail, venue, and museum micro-location use cases.

> ### Note on the "FEFD = Google Cast" claim
>
> Many ad-hoc public references say `FEFD = Google Cast / Chromecast setup`. The canonical SIG registry contradicts this — FEFD is assigned to **Gimbal, Inc.**, not Google.
>
> The likely cause of the confusion: Chromecast's now-deprecated **guest mode** broadcast FEFD as part of its discovery beacon, almost certainly because Chromecast firmware integrated Gimbal's beacon SDK in the 2014-2016 timeframe when Qualcomm Gimbal was licensing its proximity stack widely. From an identifier-ownership perspective, FEFD is still Gimbal's; the Chromecast emission was a downstream user of that identifier, not the canonical assignee.

The vendor attribution for both 0x008C and FEFD is **confidently confirmed** via the canonical Bluetooth SIG YAMLs. The 23-byte payload structure, however, is **not publicly documented** — it is high-entropy and consistent with Gimbal's MIC-protected rotating-identifier beacon frames (designed to obfuscate the underlying beacon UUID so off-deployment readers cannot trivially re-identify the hardware without a per-deployment key in Gimbal Manager). This parser therefore takes the "vendor-confirmed, payload undocumented" stance shared with [`OPPOParser`](./oppo.md) and [`AmazonHIDRemoteParser`](./amazon-hid-remote.md): it confirms the vendor and captures the raw payload bytes for downstream reverse-engineering, without speculating about field semantics.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Manufacturer-data CID | `0x008C` (little-endian raw `8c 00`) — Gimbal, Inc. |
| Service UUID | `0xFEFD` (also SIG-allocated to Gimbal, Inc.) |
| Local name | absent |
| Sample mfr-data (25 bytes) | `8c00017ec4b519a3c0e249cab44cdba36e7f25fc8f8564a321` |
| Unique emitters | 1 |
| Sightings | 5 (sustained — same device for ~10 seconds) |

The parser matches on **CID 0x008C OR service UUID FEFD**. Either alone is defensible because the SIG canonical registry allocates both to the same vendor; the pair together is the strongest signal and produces the richest metadata.

### Payload bytes (capture from `research/adwatch_export 8.json`, May 2026)

```
8c 00 | 01 7e c4 b5 19 a3 c0 e2 49 ca b4 4c db a3 6e 7f 25 fc 8f 85 64 a3 21
 CID  | 23-byte payload
```

### Stable Key

```
gimbal:<mac>
```

The advertised BD_ADDR was random in this capture (Gimbal beacons typically rotate). Without a recoverable serial (the 23-byte payload is opaque), the stable key falls back to MAC-scoped.

## What we DID figure out

- **Vendor**: Gimbal, Inc. (confirmed against two independent canonical SIG sources — `company_identifiers.yaml` *and* `member_uuids.yaml`).
- **Unusual dual-identifier ownership**: Gimbal is one of relatively few vendors that holds both a CID and a member service UUID. The combined fingerprint `CID 0x008C + serviceUUID FEFD` is highly specific.
- **Hardware family**: Gimbal Series 10 / 20 / 21 BLE proximity beacons (and beacon-firmware-licensed devices built on the Gimbal stack — historically including Chromecast guest-mode broadcasts).

## What we did NOT figure out

- **Field semantics of the 23-byte payload.** No publicly available documentation describes the Gimbal beacon frame format below the SDK abstraction layer. Searches across:
  - Gimbal's developer documentation (`docs.gimbal.com`) — covers the SDK API surface but not the wire format.
  - `reelyactive/advlib-ble-manufacturers` decoder library.
  - Nordic `bluetooth-numbers-database`.
  - General BLE reverse-engineering blogs / forums.

  …all return nothing actionable. Gimbal's frames are MIC-protected and require a per-deployment key held in **Gimbal Manager** (the cloud-side console) to decrypt, by design.

- **Speculative patterns visible to the eye** (with too little data to defend):
  - byte 0 `0x01` could be a frame-type discriminator (Series 10 vs Series 21 vs visitor-tracking vs configuration).
  - The remaining 22 bytes are high-entropy with no obvious repeated structure, consistent with a MIC-protected rotating identifier rather than a fixed-layout sensor frame.

  With only **one sustained capture**, we cannot tell which bytes are static identity, which rotate, and which encode state — so the parser deliberately decodes nothing.

- **Product class / model.** Without a local name and with an opaque payload, we cannot tell which specific Gimbal SKU (Series 10, 20, 21, or a licensed firmware device) is broadcasting. The parser sets `deviceClass = "beacon"` because the SIG identifiers themselves attest to the proximity-beacon role.

## Pipeline registration

Routed by manufacturer-data CID **and** by the FEFD service UUID:

```swift
registry.register(parser: GimbalParser(), companyID: 0x008C)
registry.register(parser: GimbalParser(), serviceUUID: "0000fefd-0000-1000-8000-00805f9b34fb")
```

Either match is sufficient — the parser internally validates both signals when present and surfaces whichever metadata is available. Registering both routes ensures the parser is consulted whether the emitter broadcasts the CID alone, FEFD alone, or both together.

## Future work

When a second Gimbal capture is observed (different emitter or different time window), diff the 23-byte payloads to identify:
1. **Frame-type byte** (first byte) — does it stay `0x01`, or does it cycle through other values?
2. **Rotating vs static regions** — by aligning two captures from the same hardware ~minutes apart, we may be able to identify the rotating-identifier window (typically a counter or pseudorandom nonce) and the static encrypted-payload tail.
3. **Series discriminator** — Gimbal Series 10 vs 20 vs 21 may have distinct frame layouts.

Without the per-deployment key, full decryption is out of scope, but identifying which bytes are static would let us derive a more stable identity hash than the rotating BD_ADDR.

## References

- [Bluetooth SIG company identifiers (canonical YAML)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — `0x008C` = Gimbal, Inc.
- [Bluetooth SIG member UUIDs (canonical YAML)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — `0xFEFD` = Gimbal, Inc.
- [Nordic Semiconductor bluetooth-numbers-database](https://github.com/NordicSemiconductor/bluetooth-numbers-database) — mirror confirming `0x008C` = Gimbal, Inc.
- [Gimbal Proximity overview / SDK docs](https://docs.gimbal.com/proximity_overview.html)
- [Gimbal Proximity beacon hardware store (Infillion)](https://store.gimbal.com/)
- [SEC 8-K — Qualcomm Gimbal spin-out (2014)](https://www.sec.gov/Archives/edgar/data/0000804328/000123445214000304/qcom1015148-kex991.htm)
- [Chromecast guest-mode BT/Wi-Fi beacon (Google Support)](https://support.google.com/chromecast/answer/6109292) — historical user of FEFD before guest-mode deprecation.
- `research/adwatch_export 8.json` — one captured Gimbal emitter (5 sightings).
