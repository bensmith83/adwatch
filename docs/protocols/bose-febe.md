# Bose FEBE Earbud / SoundLink Plugin

## Overview

Bose's newer product lines — **QC Ultra Earbuds**, **Open Earbuds Ultra**, and likely the SoundLink Micro 2 / Frames generation — advertise under a different Bluetooth SIG company identifier (`0x009E`) than the older Bose audio devices the existing `BoseParser` covers (`0x0065`). They consistently co-advertise SIG member service UUID `0xFEBE` (Bose Corporation's secondary service).

This parser is a sibling of `BoseParser`: both vend "is this a Bose audio device?" classifications, but they decode different on-wire formats from different SIG IDs. We chose a separate parser rather than extending `BoseParser` because the payload structure is sufficiently different that a unified parser would be twice as complex with no benefit.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x009E` | Newer Bose SIG identifier (canonical). |
| Company ID | `0x4703` | On-wire `03 47` — Telink big-endian-quirk; see § below. |
| Company ID | `0x3703` | On-wire `03 37` — Bose+Telink vanity / unregistered; see § below. |
| Service UUID | `0xFEBE` | SIG-registered to Bose Corporation; required alongside all non-`0x009E` CIDs. |
| Local name (when broadcast) | `"Bose Open Earbuds Ultra"`, `"Bose QC Ultra Earbuds"`, `"LE-Connies Bose"`, … | User-renameable in the Bose Music app. |

### Manufacturer Data Layout (9 bytes after company ID)

```
Byte 0     : flags / record-version (0x00 in all observed captures)
Byte 1     : product code (varies per SKU)
Byte 2     : 0x06 (model-family magic byte; constant)
Bytes 3..8 : 6-byte per-device rolling hash
```

### Product Code Map

| `product_code` | Observed local name |
|---|---|
| `0x24` | `"Bose QC Ultra Earbuds"` (and a user-renamed instance: `"Niggapods"`) |
| `0x82` | `"Bose Open Earbuds Ultra"` |
| `0x2C` | (no local name captured) |

The parser surfaces `suggested_product` for known codes and `renamed = true` when the device's local name doesn't start with one of the official Bose prefixes (`"Bose "`, `"LE-Bose "`, `"LE-"`).

### Rolling Hash

The trailing 6 bytes change between consecutive sightings of the same physical earbud — so they are **not** a stable device serial. They look like a 48-bit rolling identifier the Bose Music app validates during pairing. Within a short time window, two consecutive ads from the same earbud share the same hash; that's enough to use as a same-burst stable key but you should not expect it to persist across reboots.

## Detection Significance

- **High-end personal audio in earshot.** Bose QC Ultra and Open Earbuds Ultra retail at $300+; their presence in a scan is a strong consumer-electronics signal.
- **Renamed earbuds are common.** The "Niggapods" sample in our dataset is an extreme example, but renaming earbuds via the Bose Music app is a routine personalization — we flag renamed devices with `renamed = true` so downstream tooling can decide whether to display the user-supplied name.

## What We Cannot Parse from Advertisements

- Per-unit serial — the 6-byte hash is rolling, not a stable serial. To get a true serial number you'd need to GATT-connect and read the Device Information service.
- Battery / charge state — likely in the GATT vendor service, not in the advertisement.

## Coexistence with BoseParser

This parser handles SIG CID `0x009E` and the `0xFEBE` service UUID. The existing `BoseParser` handles SIG CID `0x0065` (older Bose product lines: SoundLink, QC 35/45, Frames) and the `0xFE78` service UUID. They cover disjoint Bose product generations and do not conflict.

## Telink-BE Byte-Order Quirk (CID `0x4703` → true SIG CID `0x0347`)

A subset of Bose products — observed in May 2026 with the local-name string `"LE-Bose QC Headphones"` and on a handful of co-located anonymous emitters (one of which broadcast `"LE-Smoke"`) — ship with a **Telink Semiconductor (Shanghai) BLE SoC** (TLSR8232/TLSR8278 family). Certain Telink reference-firmware SDK versions transmit the manufacturer-data SIG company identifier in **big-endian byte order** rather than the little-endian required by Bluetooth Core 5.x § 2.3.1.

- On-wire bytes: `03 47` …
- LE-correct decode: **`0x4703`** (what `RawAdvertisement.companyID` reports).
- True SIG-assigned CID: **`0x0347` Telink Semiconductor (Shanghai) Co., Ltd.**

The same byte-order bug is already documented elsewhere in this codebase for **Nespresso** (`0x0225` → on-wire `0x2502`).

### Observed Payload Variants

| Manufacturer-data hex (CID + payload) | Length | Local name observed |
|---|---|---|
| `03 47 52 10 e1 97 28 52 3c ca 76 ea 56` | 13 B | `"LE-Smoke"` (also seen anonymous) |
| `03 47 51 10 5d 28 cb 76 50 b7 47 2c 36` | 13 B | `"LE-Bose QC Headphones"` |
| `03 47 41 08 e2 1a de ba 61 81` | 10 B | (no name captured) |
| `03 47 41 08 e0 cd ef e1 07 d1` | 10 B | (no name captured) |

Two payload sub-formats with a 2-byte type/length prefix (`41 08`, `51 10`, `52 10`) followed by what looks like a per-device rolling identifier. The structure is heterogeneous enough that the parser surfaces raw bytes plus provenance metadata rather than attempting a per-byte semantic decode.

### Detection Logic

CID `0x4703` + FEBE service UUID is itself a high-confidence Bose+Telink signature, so the parser **does not require** a `"Bose"` substring in the local name on this path (unlike the vanity-CID path). The trigger is unique because no SIG-assigned CID legitimately decodes as `0x4703` — the only way a real BLE radio emits those bytes is via the Telink BE quirk.

### Surfaced Metadata

| Key | Value |
|---|---|
| `wire_format` | `"bose_febe_telink_be"` |
| `cid_encoding` | `"big_endian_quirk"` |
| `chip_vendor` | `"Telink Semiconductor (Shanghai)"` |
| `true_sig_cid` | `"0x0347"` |
| `company_id` | `"0x4703"` (the LE-decoded value) |
| `payload_hex` | hex of bytes after the 2-byte CID |
| `product` | local name when broadcast, else `"Bose (Telink/FEBE)"` |

## Vanity CID variant: 0x3703 (unregistered)

A third Bose variant — observed in May 2026 with the local-name string `"LE-Connies Bose"` (and a handful of anonymous emitters with no broadcast name) — advertises with on-wire CID bytes `03 37` (**LE-decoded as `0x3703`**) alongside the FEBE service UUID.

Unlike the `0x4703` path above, `0x3703` is **NOT** a byte-order quirk: `0x3703` is not in the SIG-assigned CID registry (current max ≈ `0x10C7`), so this is a **vanity / unregistered company identifier** — a vendor's forged choice rather than a buggy encoding of a registered ID. The Bose attribution comes from the co-advertised FEBE service UUID (registered to Bose Corporation); the parser will not claim on `0x3703` alone.

The working hypothesis is that this is another Bose product family on a Telink Semiconductor (Shanghai) BLE SoC, distinct from the SKUs in the `0x4703` capture set.

### Observed Payloads

| Manufacturer-data hex (CID + payload) | Length | Local name observed |
|---|---|---|
| `03 37 72 10 05 bd 53 4a eb d9 ad 15 bc 50 e1 b5` | 16 B | (no name captured) |
| `03 37 51 10 70 2a 2b 12 16 a5 cb 9a e4` | 13 B | `"LE-Connies Bose"`, also seen anonymous |

Payload byte 0 carries a **product code** (`0x72`, `0x51` observed) — distinct from the `0x009E` canonical layout where the product code lives at payload byte 1, and distinct from the `0x4703` Telink-BE layout where bytes 0..1 are a 2-byte type/length prefix. The remaining bytes look like a per-device rolling hash; we surface them as `device_hash_hex` without claiming they are a stable serial.

### Detection Logic

Parser keys on **CID `0x3703` + FEBE service UUID**, with no `"Bose"` substring required in the local name (the captured frames are often anonymous). FEBE is the attribution anchor — `0x3703` alone never claims.

### Surfaced Metadata

| Key | Value |
|---|---|
| `wire_format` | `"bose_febe_vanity_3703"` |
| `cid_encoding` | `"vanity_unregistered"` |
| `chip_vendor` | `"Telink Semiconductor (Shanghai)"` |
| `company_id` | `"0x3703"` (the LE-decoded value) |
| `product_code` | hex of payload byte 0 (e.g. `"0x72"`, `"0x51"`) |
| `device_hash_hex` | hex of payload bytes 1..end |
| `payload_hex` | hex of all bytes after the 2-byte CID |
| `local_name` | local name when broadcast |
| `product` | local name when broadcast, else `"Bose (FEBE/3703)"` |

## References

- [Bluetooth SIG member UUIDs (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — confirms `0xFEBE = Bose Corporation`.
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — full CID registry; confirms `0x3703` is unassigned and `0x0347 = Telink Semiconductor (Shanghai) Co., Ltd.`.
- [Telink Semiconductor TLSR8232 / TLSR8278 BLE SoC product page](https://www.telink-semi.com/products-tlsr8278.html)
- [Bose QC Ultra Earbuds product page](https://www.bose.com/p/quietcomfort-ultra-earbuds)
- [Bose Music app](https://www.bose.com/c/bose-music-app)
