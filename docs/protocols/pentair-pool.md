# Pentair Pool / Spa Controllers

## Overview

Pentair's pool and spa equipment uses BLE for both Pentair Home
app onboarding (Wi-Fi handoff) and direct device control when out
of Wi-Fi range. Multiple product families share the same BLE
fingerprint: EasyTouch and IntelliCenter (pool automation
controllers), IntelliSync (gateway for legacy gear),
IntelliFlo3 / IntelliFlo3 VSF (variable-speed pumps),
IntelliConnect (pump connector), ScreenLogic (IP gateway),
and MasterTemp (gas heaters).

The advertisement is identity-only. Pump RPM, water temperature,
heater state, etc. live behind the authenticated GATT control
surface and the ScreenLogic TCP/IP protocol on the LAN.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0x0D18` | **Vendor-claimed, NOT SIG-assigned.** Used across the Pentair BLE lineup. |
| Local name | `<Product> <serial>` | e.g. `EasyTouch 352015364`, `IntelliCenter 123456789` |

The 16-bit UUID `0x0D18` does not appear in any SIG-allocated UUID
yaml (member_uuids or service_uuids). Pentair claims it as a
vendor fingerprint without registration. It is the most reliable
single anchor for Pentair-class detection.

## Local Name Decoding

```
"EasyTouch 352015364"
 └────┬───┘ └────┬────┘
      │          └── 6–12 digit unit serial
      └── product-line prefix
```

| Product | Class |
|---------|-------|
| `EasyTouch` | Pool automation controller (legacy + Wi-Fi retrofit) |
| `IntelliCenter` | Pool automation controller (current gen) |
| `IntelliSync` | Gateway for legacy gear |
| `IntelliFlo3` | Variable-speed pool pump |
| `IntelliConnect` | Pump connector kit |
| `ScreenLogic` | IP gateway (BLE used for onboarding) |
| `MasterTemp` | Gas pool/spa heater (with the Wi-Fi/BT kit) |

The serial alone does not reveal the sub-model (EasyTouch 4 vs 8,
IntelliFlo3 vs IntelliFlo3 VSF, etc.) — that requires a Pentair-internal
SKU table not in the public docs. We capture the visible name as
`product` and the digits as `serial`; treat the model granularity as
provisional.

## Wire Format

No structured payload — there is no manufacturer-data. The product
identity comes entirely from the local name; the `0x0D18` service
UUID acts as the vendor anchor.

## Identity Hashing

```
identifier_hash = SHA256("{product}:{serial}")[:16]   # preferred
identifier_hash = SHA256(mac_address)[:16]            # fallback when name absent
```

Product+serial is stable per physical unit across BLE MAC rotation.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | UUID + name | Pentair |
| Product line | local name prefix | EasyTouch / IntelliCenter / etc. |
| Serial | local name suffix | 6–12 digit string |

## What Requires GATT or ScreenLogic Connection

- Pump RPM / power
- Water temperature
- Heater state (on/off, mode)
- Pool light state
- Salt cell level
- Filter cycle status
- Chemistry readings (when paired with IntelliChem)

The ScreenLogic TCP/IP protocol on the local network exposes most
of those without BLE; the BLE GATT surface mirrors a subset for
out-of-Wi-Fi control via Pentair Home.

## References

- `tagyoureit/nodejs-poolController` — RS-485 / ScreenLogic
  reference implementation (no BLE — confirms ScreenLogic is
  IP-only)
- Home Assistant `screenlogic` integration (TCP/IP-only)
- Pentair Home pairing flow docs (IntelliSync user's guide,
  IntelliFlo3 VSF pairing guide)
- Bluetooth SIG `member_uuids.yaml` — confirms `0x0D18` is not a
  registered SIG UUID
