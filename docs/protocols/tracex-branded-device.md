# TraceX-Branded BLE Device — Vendor Unattributed

## Overview

Captured BLE peripherals advertise the literal brand string `TraceX`
followed by a 1–6 digit numeric serial, gated on a single 128-bit
vendor service UUID. The actual vendor and product are currently
**unattributed**.

An earlier pass attributed this fingerprint to TraceX Inc.
(Landenberg, PA — FCC grantee `2A3UI`) and its Affirm court-ordered
alcohol-monitoring anklet. **That attribution was retracted** on
re-audit; the evidence is laid out under "What this is NOT" below. The
parser is kept as a brand-prefix + service-UUID fingerprint cluster so
captures don't drift unparsed, but no longer claims product = "Affirm"
and no longer sets `sensitive=true`.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0000A100-8501-11E3-BA12-0002A5D5C51B` | 128-bit vendor UUID; required for match |
| Local name | `TraceX<digits>` (optional) | e.g. `TraceX13859` — `\d{1,6}` numeric suffix is the device serial |
| Manufacturer data | *(none)* | name + UUID only |
| Service data | *(none)* | |
| Address type | `random` | rotating private address |

A match requires **the full 128-bit vendor UUID**. Do not match on the
`0002A5D5C51B` UUIDv1-node suffix alone — that suffix is a shared
toolchain artifact also present on Oura Ring and Nespresso vendor
UUIDs already covered by other parsers.

### What the UUID tells us

The vendor UUID is a UUIDv1 (time + MAC-node, RFC 4122):

- Version nibble `1` (the `1` in `11E3`)
- Embedded timestamp resolves to **2014**
- Node bytes `00:02:A5:D5:C5:1B` match the **STMicroelectronics
  BlueSTSDK** reference template (ST's BLE sensor SDK uses
  `XXXXXXXX-XXXX-11eX-XXXX-0002a5d5c51b` as a UUID base). The
  clock-seq (`BA12`) differs from ST's official `AC36`, so this is
  not ST's own SDK output — it's a developer who reused the ST node
  bytes, either by copy-pasting ST sample code or by re-seeding a
  UUID generator with the ST template.

The shared-node artifact across Oura, Nespresso, and this device
suggests a shared firmware contractor / consulting house that minted
vendor UUIDs for multiple unrelated clients ~2013–2014 from a single
workstation.

OUI `00:02:A5` has the locally-administered bit clear, so per RFC 4122
the value must have originated from a real IEEE-assigned MAC at some
point. Public OUI lookups variably attribute it to Compaq Computer
Corp (historical IEEE registry entries) and STMicroelectronics
(current public lookups) — the attribution is unresolved and
ultimately irrelevant: the node tells you about the original
developer machine, not about the captured device's vendor.

### What We Can Parse

| Field | Source | Notes |
|-------|--------|-------|
| `vendor` | hard-coded | `TraceX` — literal brand string in localName |
| `serial` | localName regex | optional; numeric suffix `\d{1,6}` |
| `deviceClass` | hard-coded | `unknown` |

### What We Cannot Parse from the Advertisement

- Vendor identity beyond the brand string.
- Product type or SKU.
- Battery, status, sensor readings, or any per-frame payload data.

## What this is NOT — the Affirm anklet attribution, retracted

An earlier pass claimed this advertisement came from the **TraceX
Inc. Affirm** court-ordered alcohol-monitoring anklet (FCC grantee
2A3UI, modular approval 2A3UI-TX4871). That attribution failed three
independent checks on re-audit:

1. **Wrong Bluetooth mode.** The FCC user manual for the Affirm
   anklet shows it exposes **Bluetooth Classic SPP** (pairing PIN
   `1234`), with local name **`Alcohol Anklet`** or **`HC-06`** — the
   default for a Microchip BM71 in serial-bridge mode. The Affirm
   anklet does NOT advertise as a BLE peripheral named `TraceX####`.
2. **Wrong duty cycle.** Per the Affirm manual, the anklet's
   Bluetooth radio is normally OFF — only activated when the charger
   is connected or when a magnet is held over the LED location to
   wake the radio. A continuously-advertising peripheral observed in
   ambient consumer BLE scanning is inconsistent with that.
3. **Wrong chipset family for the UUID.** The Affirm anklet uses a
   **Microchip BM71** module (confirmed by FCC user-manual exhibit:
   "HVIN: BM71BLES1FC2", "BT SIG/QDID: 74246"). The captured UUID
   `0000A100-8501-11E3-BA12-0002A5D5C51B` matches the
   STMicroelectronics BlueSTSDK reference template — a different
   BLE silicon ecosystem. Microchip BM7x firmware does not use this
   UUID template.

### Other "TraceX" vendors are not stronger candidates

| Vendor | What they make | Has wireless hardware? |
|--------|----------------|------------------------|
| TraceX Inc. (Landenberg, PA) | Affirm anklet | Yes, but ruled out above |
| TraceX Technologies (Bengaluru) | Pure SaaS blockchain for food / livestock traceability — no devices | No |
| TraceX Labs (India) | AI cybersecurity / mobile security — SaaS only | No |
| TraceX (Montreal) | Fitness rewards smartphone app — phone GPS only | No |

`2A3UI` is the **only** FCC grantee with "TraceX" in the name. No
public English-language search has surfaced a vendor whose hardware
fits the observed pattern (`TraceX####` BLE name + ST-template
vendor UUID + continuous advertising).

### What additional evidence would resolve attribution

- An internal-photo or label-and-location FCC exhibit for any
  `TraceX#####`-branded device under a non-TraceX-named grantee
  (the brand could be OEM-licensed or owned by a parent company
  filing under a different name).
- A GATT walk of one of these devices — the service UUID `0000A100`
  is a vendor primary service; reading its characteristics (and the
  Device Information Service `0x180A`) would expose a manufacturer
  name string.
- A USPTO trademark search for "TraceX" in goods-in-class IC 9
  (electronic apparatus) to enumerate live and dead marks.
- Location-clustered captures — if `TraceX####` sightings
  concentrate at a specific facility type, that constrains the
  product category.

## Stable Identity

When the serial is captured, it's the stable per-unit identifier and
persists across rotating BLE address changes:

```
stable_key = tracex_branded_device:<serial>
```

When only the nameless UUID-only sibling frames are captured, fall
back to the (rotating) MAC:

```
stable_key = tracex_branded_device:<mac>
```

A typical capture chain may show alternating named and nameless
frames from the same physical device on the same MAC — pair them to
recover the serial.

## Detection Significance

- Currently unknown. The earlier compliance-monitoring framing was
  load-bearing on the Affirm attribution and does not apply.
- Treat any `TraceX####` capture as standard ambient BLE until
  vendor attribution lands.

## References

- [TraceX Inc. — Affirm product line](https://tracexinc.com/) — ruled out as the source of this advertisement
- [FCC grantee 2A3UI — TraceX Inc.](https://fccid.io/2A3UI)
- [FCC filing for TraceX BM71 BLE module (host Affirm A 002)](https://fccid.io/2A3UI-TX4871) — note that the BM7x family is **Microchip Technology**'s (BM70/BM71/BM78, originating from Microchip's acquisition of Roving Networks), not STMicroelectronics's BLE silicon
- [TraceX Affirm spec sheet PDF (tracexinc.com)](https://tracexinc.com/wp-content/uploads/2018/05/Affirm-spec-sheet-20180506-3.pdf)
- [TraceX Tech (agriculture SaaS)](https://tracextech.com/) — not the source (no hardware)
- [STMicroelectronics BlueSTSDK_Python (UUID base reference)](https://github.com/STMicroelectronics/BlueSTSDK_Python) — origin of the `0002a5d5c51b` node template
- Note on the shared `…0002A5D5C51B` UUIDv1-node suffix: see
  `docs/protocols/nespresso.md` and `docs/protocols/oura-ring.md` for
  the other vendors that share it. The collision is a toolchain
  artifact, not a per-vendor identifier.
