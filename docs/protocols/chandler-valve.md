# Chandler Systems Water-Treatment Control Valve (CID 0x073A)

## Overview

Chandler Systems Inc. holds Bluetooth SIG **company identifier `0x073A`**.
Chandler manufactures water-treatment control
heads (water softeners, backwashing filters, iron filters, aeration
systems) that are also white-labelled as **SpringWell**, **Nelsen**,
**WaterSoft** and **Clearion**. The C6-series ("Signature" / "Connected
Series") boards expose a Bluetooth link driven by the **Legacy View**
app; the valve advertises continuously so the app can find it in range.

Six nameless records / 270 sightings captured in the 2026-10-17 sweep,
each a 10-byte manufacturer frame on CID 0x073A co-advertising the
**SMP / MCUmgr DFU service UUID** `8d53dc1d-1db7-4cd3-868b-8a527460aa84`,
random BLE address, no local name. Attribution is vendor-confirmed, not
inferred: Chandler's own firmware engineer stated in the Home Assistant
community thread (2025-04) that the `8d53dc1d…` service is their MCUmgr
SMP DFU service (the "bee" services `a725458c-bee1/2/3-…` are the real
app-facing valve services), and the community-reverse-engineered
`ha-chandler-legacy-view` integration (sharwell) publishes the full
manufacturer frame. This doc ports its `discovery.py` decode.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x073A` (wire `3a 07`) | SIG-assigned to Chandler Systems Inc. |
| Service UUID | `8d53dc1d-1db7-4cd3-868b-8a527460aa84` | SMP/MCUmgr DFU; corroboration, not a gate |
| Payload length | 8 / 9 / 10 / 12 bytes (after CID) | firmware + layout gate |
| Firmware bytes | last 2 payload bytes | BCD-ish (`06 12` → "C6.12"); picks the layout |

### Byte Layout

The manufacturer frame is **CID (2 bytes) + payload**. Firmware version
= `major*100 + minor`, decoded from the last two payload bytes; the
version selects the layout.

**Evb034** (firmware ≥ C6.00, 8-byte payload):

```
Offset  Field
------  -----
3a 07   Company ID 0x073A
 0      valve status — bit7 salt sensor, bit6 water status, bit5 bypass
 1      valve error code
 2      clock hours
 3      clock minutes
 4      valve type code (see table)
 5      valve series version
 6      firmware major (BCD-ish)
 7      firmware minor (BCD-ish)
```

**Evb019** (firmware < C6.00, 9/10/12-byte payload) renumbers the status
bits (bit0 auth required, bit1 salt, bit2 water, bit3 bypass) and adds a
bootloader version, connection counter and radio-protocol version at
offsets 4+. The `ha-chandler-legacy-view` `_parse_evb019_payload` is the
reference for the longer layouts; only the Evb034 shape is captured in
the NearSight corpus so far.

### Valve type codes (standard, snake_cased)

`1`/`3`/`19`/`21` metered_softener, `2` time_clock_softener,
`4`/`5`/`6`/`7`/`20`/`22`/`26`/`27` backwashing_filter, `8` ultra_filter,
`9`/`11` centurion_nitro, `10`/`12` centurion_nitro_sidekick,
`13` nitro_pro, `14`/`15` nitro_pro_sidekick, `16`
centurion_nitro_sidekick_v3, `17` commercial_metered_softener,
`18` commercial_backwashing_filter, `23` nitro_filter, `24` sidekick,
`25` commercial_aeration.

## Parser Scope (Passive Only)

`ChandlerValveParser` (`chandler_valve`, deviceClass `appliance`):

- Gates on CID 0x073A AND a payload length of 8/9/10/12 AND a
  firmware version that decodes non-zero AND a layout consistent with
  that version. Short status/counter packets (no firmware bytes) are
  left unclaimed.
- Emits model (`Evb034`/`Evb019`), firmware version, valve status bits
  (salt / water / bypass), error code, clock hours/minutes, valve type
  and series.
- Identity is **address-anchored** (no stableKey): the frame carries no
  serial or per-unit identifier, only clock + status.

## Attribution Confidence

**Vendor: high** — SIG CID 0x073A is Chandler's own slot and the vendor's
engineer confirmed the service split by name. **Decode: high** — the
layout is published reverse engineering, not inference. **Identity:
low** — no per-unit identifier exists in the advertisement.

## References

- Bluetooth SIG Assigned Numbers — company identifier 0x073A
- [Home Assistant thread: "Chandler Water Filter"](https://community.home-assistant.io/t/bluetooth-integrations-chandler-water-filter-and-homedics-drift/543388)
- [ha-chandler-legacy-view](https://github.com/sharwell/ha-chandler-legacy-view) — `discovery.py` reference decode
- [ha-chandler-signature](https://github.com/hessenpepper/ha-chandler-signature) — the newer C6.13+ token-authenticated API
- NearSight app research write-up `research/sweep-2026-10-17-candidates.md`
