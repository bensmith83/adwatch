# Owner-labelled Ubiquiti-block Sensor (parser `fa_flem_sensor`; product not identified)

> The parser id and this file name are legacy identifiers kept for cross-repo
> references; the owner-chosen local name they were derived from is redacted below.

## Overview

A BLE sensor observed in the 2026-07-06 sweep, identified by a **custom 128-bit
vendor UUID** `35CD221C-02B4-4D1F-9B54-6089C861AD62`. A random 128-bit UUID is
globally unique to whoever minted it, so keying on the full string is a
near-zero-false-positive anchor. **Low-trust-sourced.**

The vendor is **Ubiquiti**: the frame carries the unit's factory MAC under
service data `0x252A`, and that MAC sits on an IEEE MA-L block registered to
Ubiquiti Inc. The **product is not known.**

## Attribution (corrected)

The 2026-07-06 write-up read the local name `<owner-chosen label>` as
"tentatively a vehicle-maker temperature probe" and never looked the MAC up. That reading
is **retracted**. The evidence, strongest first:

1. **MAC block.** The `0x252A` value `58:d6:1f:xx:xx:xx` is on IEEE MA-L block
   `58:D6:1F`, registered to **Ubiquiti Inc** (the research repo's vendored
   registry, `_oui_vendors.py`, lists `58D61F` under that name).
2. **Convention.** "Service data `0x252A` carries the unit's factory MAC" is
   Ubiquiti's own beacon convention: the UniFi access-point adoption beacon
   uses it (`ubiquiti-unifi.md`) and so do three more Ubiquiti product-line
   UUIDs on `24:5A:4C` / `70:A7:41` / `F4:E2:C6` (`ubiquiti-device-beacon.md`).
   This frame is the fourth product-line UUID on that convention.
3. **Neighbouring key.** The `0x2120` service-data key sits beside the UniFi
   `0x2119` / `0x2021` keys (Ubiquiti units on `1C:6A:1B` in the 2026-09-29
   sweep advertised `2120`, `2021` and `2119` together). Corroborating, not
   proof: the 1-byte `0x2120` value here is undecoded.

One block is thinner evidence than the three independent blocks behind
`ubiquiti-device-beacon`, but a factory-MAC block plus the shared `0x252A`
convention is two independent signals that agree.

The local name is **not** evidence of the maker. `<owner-chosen label>` is
free text that whoever set the unit up chose (a Ubiquiti product lets its owner
or installer name the device), so the label is something someone typed, most
plausibly for where or what the sensor monitors, not a part number. It
reads as that owner's site / unit naming. It is recorded as
`device_name` and nothing more.

**Product: unknown.** Nothing in the frame names a Ubiquiti product line. A
UniFi Protect / environmental sensor is the obvious *hypothesis* given the
`sensor` device class and a temperature-flavoured name, but no byte in the frame
supports it, so the parser does not claim it (`product_family = unknown`).

## Identification

| Signal | Value | Notes |
|---|---|---|
| Service UUID (128-bit) | `35CD221C-02B4-4D1F-9B54-6089C861AD62` | custom UUID — the routing anchor |
| Service data `0x252A` | `58 d6 1f xx xx xx` | 6-byte **factory MAC**; OUI `58:D6:1F` = Ubiquiti Inc |
| Service data `0x2120` | `0b` | opaque 1-byte counter/flag (named variant only) |
| Local name | `<owner-chosen label>` | present on one of two frames; user/installer-chosen label |
| Manufacturer data | none | |
| Device class | `sensor` | kept; the class was never the doubtful part |

## Match rule

Match on the custom vendor UUID (case-insensitive). Vendor = the `0x252A` MAC's
OUI resolved through NearSight's curated OUI table (`58:D6:1F` → "Ubiquiti
Networks"); a frame whose MAC resolves to no curated vendor carries no vendor
line. Parser: `FAFlemSensorParser` (`fa_flem_sensor`).

**Identity is unchanged by the re-attribution.** Stable key =
`fa_flem_sensor:<0x252A id as lowercase hex>` (so both frames of one device map
together, BLE-address-rotation-proof), identifier hash = the first 16 hex chars
of its SHA-256, device class `sensor`. Emitted metadata: `vendor`, `oui`,
`oui_vendor`, `product_family = unknown`, `attribution = oui`,
`attribution_note`, `vendor_uuid`, `device_id_hex`, `counter_hex`, `device_name`.

## Why this is not folded into `ubiquiti_device_beacon`

`ubiquiti_device_beacon` routes on the `0x252A` key and gates on a Ubiquiti OUI,
with identity `ubiquiti_device_beacon:<colon-separated mac>` and device class
`unknown`. This parser routes on its own vendor UUID, keys on
`fa_flem_sensor:<hex mac>` and reports `sensor`. Folding would change the parser
id, stable key and identifier hash of every stored record of this device, a
migration for a one-device, 15-sighting cluster. The two parsers instead share
the vendor attribution: `ubiquiti_device_beacon` hands this UUID off untouched
(it also declines the UniFi-AP UUID), so a frame has exactly one claimant.

## Open questions

- Which Ubiquiti product advertises `35CD221C-…`? A sighting with a model name,
  an adoption flag or a UniFi `0x2119` counter beside it would settle it.
- What `0x2120` (`0b`) carries. It appears only on the named variant.
- Byte-semantic decode stays deferred: one physical device, 15 sightings.
