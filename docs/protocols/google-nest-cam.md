# Google Nest Cam (2nd gen) BLE Protocol

## Overview

The 2nd-generation **Nest Cam** (battery + wired) and the Nest Doorbell family
advertise an 11-byte manufacturer-data frame whose first three bytes literally
spell a Google/Nest **IEEE OUI**, alongside a Google-proprietary 128-bit
service UUID and (sometimes) the localName `Nest Cam`.

This is **distinct** from `google-nest.md` / `NestParser`, which handles the
older `0xFEAF` service-data frame used by thermostats, original cameras,
Nest Mini/Hub, Protect, etc. A single physical Nest Cam alternates between a
named frame (localName `Nest Cam`) and a nameless sibling frame in the same
advertising window.

## Identification

| Signal | Value | Notes |
|---|---|---|
| Vendor service UUID (128-bit) | `D2D3F8EF-9C99-4D9C-A2B3-91C85D44326C` | Google-proprietary; not SIG-registered |
| Local name | `Nest Cam` | Sometimes absent on alternating frames |
| Manufacturer data | 11 bytes; first 3 bytes = a Google/Nest OUI (see frames) | The leading 2 bytes read little-endian look like a "company ID" but are just the OUI — neither value is a real SIG company id |
| Device class | `camera` | |

## Frame variants

Two OUI-spelled manufacturer frames are known. Both carry the same
`D2D3F8EF-…` vendor UUID, which is the routing/attribution anchor.

### Frame A — OUI `44:BB:3B` (CID 0xBB44 LE)

Fully structured; the constant bytes fingerprint the format:

| Offset | Value | Meaning |
|---|---|---|
| 0–2 | `44 BB 3B` | Google OUI `44:BB:3B` (assigned to Google Inc.) |
| 3–4 | varies | frame body |
| 5 | `DE` | sub-frame marker |
| 6 | `02` | sub-frame subtype/length |
| 7–10 | varies | rotating 4-byte identifier |

Sample: `44bb3b029fde026c407aa1`. Match accepts vendor UUID **or** `Nest Cam`
name (plus the constant bytes + 11-byte length).

### Frame B — OUI `64:16:66` (CID 0x1664 LE) — added 2026-07-06

The first three bytes spell the **IEEE-registered Nest Labs Inc. OUI
`64:16:66`** (Google-owned) — exactly parallel to Frame A's `44:BB:3B`.

| Offset | Value | Meaning |
|---|---|---|
| 0–2 | `64 16 66` | Nest Labs OUI `64:16:66` |
| 3–10 | opaque | inner bytes differ from Frame A; seen on ONE device in one short window → treated as opaque/possibly-rotating, **not decoded** |

Sample: `641666e19bac02c03e1e2a` (localName `Nest Cam`; also a nameless
sibling with the same payload + vendor UUID).

**Match rule for Frame B:** manufacturer data starts `641666` **and** length
== 11 bytes **and** the vendor UUID is present. The vendor UUID is
**required** here (not name-or-UUID like Frame A) because a bare 3-byte OUI is
a real IEEE prefix that could collide in a larger corpus, whereas the 128-bit
vendor UUID is airtight.

## Metadata surfaced

`vendor = Google`, `product = Nest Cam`, `oui` (`44bb3b` / `641666`),
`frame_variant` (`oui_44bb3b` / `oui_641666`), `frame_type_hex` (byte[2]),
`rotating_id_hex` (bytes 7–10), `payload_hex` (bytes 2–10).

## Stable key

```
google_nest_cam:<mac>:<rotating_id_hex>
```

MAC-scoped with the rotating tail appended. Bytes 7–10 are presumed
privacy-rotating per address-rotation cycle, so they are not a stable
per-device serial; identity is anchored on the MAC.

## Scope / confidence

- **Attribution: HIGH.** The device announces itself (name `Nest Cam`), carries
  a Google-proprietary vendor UUID, and its manufacturer bytes spell a real
  Google/Nest IEEE OUI. This is not a speculative byte-pattern guess.
- **Sighting support: LOW for Frame B** (one device, one short window). We ship
  a conservative **identifier/labeler** and deliberately do not decode the
  inner bytes until multi-device / multi-window samples confirm which bytes are
  stable vs rotating.
- Neither CID (`0xBB44`, `0x1664`) is a real SIG company identifier — both are
  above the SIG ceiling and are simply the first two OUI bytes read
  little-endian. CID-alone never claims.

## References

- IEEE `oui.txt` — `64:16:66` = **Nest Labs Inc.**; `44:BB:3B` = Google Inc.
- Bluetooth SIG `company_identifiers.yaml` — neither `0x1664` nor `0xBB44`
  present (both above the assigned max ≈ `0x10E1`).
- `google-nest.md` — the separate `0xFEAF` Nest service-data protocol.
