# OBDeleven (VW/Audi/Škoda/SEAT OBD-II Dongle)

## Overview

**OBDeleven** is a BLE-enabled OBD-II diagnostic dongle made by **Voltas
IT, LLC** (Lithuania). It plugs into the OBD-II port of a Volkswagen
Auto Group (VAG) vehicle — VW, Audi, Škoda, SEAT, Cupra — and bridges
the car's diagnostic bus to a companion phone app over BLE for fault-
code reading, long-coding (vehicle option byte programming), live
sensor monitoring, and one-touch feature unlocks.

The Gen 2 / "NextGen" hardware is the unit captured in our nearsight
export and is filed under FCC ID **`2AVJ4-OBDELEVEN2`** (FCC ID
confirms the "2" in the localName is the model generation, not a unit
number).

Internally, the dongle uses a **TI CC2540/CC2541** chipset running an
**HM-10-compatible firmware** (Jinan Huamao Technology). This is the
single most common BLE-UART module in cheap consumer hardware, and the
OBDeleven 2 inherits the module's default advertising signature
without override.

## BLE Advertisement Format

### Identification (Triple-Gated)

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `OBDeleven` or `OBDeleven <N>` | `OBDeleven` = Gen 1; `OBDeleven 2` = Gen 2 / NextGen (captured); `OBDeleven 3` = Gen 3 (anticipated) |
| Service UUID | `0xFFE0` | Standard HM-10 BLE-UART data-transfer service. Accepted in 16-bit or 128-bit canonical form |
| Manufacturer data | starts with ASCII `H` `M` (`0x48 0x4D`) | HM-10 module default advertising header. Treated as company-ID `0x4D48` by naïve parsers, but **`0x4D48` is unassigned in BT SIG `company_identifiers.yaml`** — it's literally just the ASCII string |
| Address type | `random` | iOS / Android privacy-rotated address |

A match requires **all three** gates. We deliberately reject:

- HM-10 modules with the same `48 4D` mfg header but different
  localNames (would catch generic Chinese BLE dongles, heart-rate
  clones, smart bulbs).
- "OBDeleven" name without the HM marker (would mis-match a re-flashed
  unit running custom firmware).
- "OBDeleven" name without the `FFE0` service UUID.

### Manufacturer Data Layout

Captured: `48 4D 00 1E 42 2B A9 93` (8 bytes total)

| Offset | Field | Size | Notes |
|--------|-------|------|-------|
| 0–1 | HM-10 ASCII marker | 2 | Literal `"HM"` (`0x48 0x4D`); module default |
| 2–7 | Embedded BD_ADDR | 6 | The 48-bit BLE MAC of the module, mirrored into the advertisement. Survives OS-level address rotation. **Stable identity anchor.** |

### What We Can Parse

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Voltas IT / OBDeleven` |
| Product family | hard-coded | `OBDeleven OBD-II dongle` |
| Vehicle compatibility | hard-coded | `VAG group (VW / Audi / Škoda / SEAT / Cupra)` |
| Device class | hard-coded | `obd2_dongle` |
| Generation | localName regex | trailing decimal digit; defaults to `1` if name has no suffix |
| Module signature | hard-coded | `hm10` |
| `embedded_bd_addr` | mfg data [2:8] | 6-byte BLE MAC, hex |
| `local_name` | localName | `OBDeleven` or `OBDeleven N` |

### What We Cannot Parse from the Advertisement

- Vehicle make / model / year — the dongle doesn't broadcast VIN.
- Currently-stored DTCs (diagnostic trouble codes).
- Live sensor data (RPM, coolant temp, MAF, …).
- Firmware version of the dongle.
- Whether the dongle is currently connected to a car (vs idle in a
  drawer).

All of those require either (a) the OBDeleven phone app + a paid
"Credit" subscription, or (b) a custom client speaking the proprietary
OBDeleven BLE protocol over the FFE0 / FFE1 (notify) characteristics.

## Stable Identity

The 6-byte `embedded_bd_addr` from the mfg data trailer is the
permanent BLE MAC of the HM-10 module — mirrored into the advertisement
so a host can recognize the device across OS-level address rotation.
We anchor stable identity there:

```
stable_key = obdeleven:bdaddr:<12-hex>
```

Fallback when the trailer is truncated:

```
stable_key = obdeleven:mac:<scanner-observed-mac>
```

## Detection Significance

- An OBDeleven dongle in a parking garage / driveway is a near-certain
  signal that a VAG vehicle is parked there with the dongle plugged in.
- The dongle continues to advertise even when the vehicle is off (it
  pulls a trickle of current from the OBD-II port), so it can sometimes
  be detected before the car is driven — useful for "is the car home"
  inference.
- Multiple OBDelevens in one parking lot (e.g. a VW dealership or VAG
  enthusiast meet-up) is a recognizable cluster signature.

## Cross-Vendor Heuristic Note

The "FFE0 + leading `48 4D` ASCII" signature is **not unique to
OBDeleven** — it identifies the **HM-10 module**, which ships in
dozens of unrelated cheap consumer BLE products (Arduino kits, generic
BLE-UART bridges, no-name OBD2 dongles, smart bulbs, heart-rate clones,
DIY firmware projects). A future parser could surface the HM-10 family
as its own forensic cluster; we keep that broader detection out of
this parser to avoid over-claiming.

## References

- [OBDeleven product page (NextGen)](https://obdeleven.com/products/nextgen-obdeleven-device)
- [FCC filing — 2AVJ4-OBDELEVEN2 (Gen 2)](https://fcc.report/FCC-ID/2AVJ4-OBDELEVEN2/)
- [Pen Test Partners: OBDeleven vulnerability research](https://www.pentestpartners.com/security-blog/obdeleven-vulnerability/) — context on the BLE protocol surface
- [Jinan Huamao HM-10 datasheet (community mirror)](https://www.elecrow.com/download/HM-10.pdf) — describes the `48 4D` advertising header
- BT SIG `company_identifiers.yaml` — confirms `0x4D48` is **not** an assigned company ID (the `H` `M` bytes are ASCII, not a CID)
- Nearsight export: `research/nearsight_export 2.json`, 3 sightings, 1 unit (2026-06-04)
