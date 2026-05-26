# Personal-safety panic buttons (gated)

> **Distribution gate.** This protocol is parsed only in builds where the
> Swift compile flag `PERSONAL_SAFETY_PARSERS` is defined. The flag is OFF
> by default and is turned on by setting `ADWATCH_PERSONAL_SAFETY=1` when
> invoking `swift build` / `swift test`. **App Store / public builds must
> ship with the flag off.**

## Why the gate

The products covered here are personal-safety panic buttons carried by
people seeking discreet emergency alerting — disproportionately
domestic-violence survivors, stalking victims, and people who feel
unsafe in their immediate environment. Their utility depends on being
unobtrusive to a potential adversary. A public app that passively
detects and labels them in proximity to an attacker's phone would
directly undermine the threat model they exist to serve. We don't ship
detection of them in the public binary.

The parser is preserved gated so the project owner can use it for
research / their own device inventory in a sideloaded build.

## Devices in scope

| Product | Vendor | Class | GAP name (best guess) |
|---------|--------|-------|------------------------|
| invisaWear smart jewelry | invisaWear | Smart-jewelry panic button (necklace/bracelet/scrunchie) | `invisaWear` |
| Silent Beacon panic button | Silent Beacon | Wearable panic button w/ 2-way audio | `Silent Beacon` |
| She's Birdie **Birdie+** | She's Birdie | Personal-alarm keychain w/ Bluetooth (original Birdie has no BT) | `Birdie+` |
| Wearsafe Tag | Wearsafe | Panic-button tag + live audio | `Wearsafe` |

## Detection

Identification is by GAP local name only, with **case-insensitive exact
match** against the strings above. No service UUIDs, no manufacturer-data
anchors, no MAC-OUI corroboration.

This is deliberately the weakest possible matcher: it will MISS devices
whose GAP name does not match the marketing brand (likely common,
especially for invisaWear which the Silicon Labs case study describes as
using non-connected advertise-on-press patterns), and it will NOT match a
substring (deliberately, to keep false-positive rate at zero — a device
named "My Birdie+ keychain" is *not* matched).

The gate is paired with a permissive policy on parser scope: when real
ad captures arrive, tighten with manufacturer data and service UUIDs.

## Capture data needed

We have no real advertisement captures from any of these devices. To
make this parser useful, capture:

- The GAP local name as actually advertised (often differs from the
  marketing name — e.g. `IW-<id>`, `SB-<id>`).
- Service UUIDs in the advertisement (16-bit or 128-bit).
- Manufacturer-specific data, especially the company ID. invisaWear is
  built on Silicon Labs BG22 / BGM240 modules and may advertise as such.
- Address type (public vs. random / RPA).
- Approximate cadence and TX power.

Once captured, replace the GAP-name-only matcher with the actual
fingerprint and add a manufacturer-data parser.

## Identity hashing

```
stable_key      = "personal_safety:" + mac_address
identifier_hash = SHA256(stable_key)[:16]
```

Most of these devices likely use BLE random addresses (RPA) since they're
worn on-body and rotation is expected privacy hygiene; the MAC-based
stable key will rotate with the address, which is fine for this parser
because we don't want stable cross-session identification of these
devices anyway.

## What we DON'T do, even in the gated build

- Surface alert / button-press state. Even when GATT data would let us
  infer it, the parser is passive-only by design.
- Cluster / track these devices across sessions. With RPA in use the MAC
  rotates and our stable key follows; that's intentional.
- Include them in any aggregated / shared / cloud telemetry. The gate is
  a binary-distribution gate; if downstream sinks publish parser output,
  they must also respect this gate.

## References

- invisaWear (Silicon Labs case study) — uses Silabs BG22 / BGM240
  BLE modules; product advertises on press, doesn't stay connected
  https://www.silabs.com/applications/case-studies/bluetooth-enabled-smart-jewelry-for-safety
- Silent Beacon — https://silentbeacon.com/
- She's Birdie — https://www.shesbirdie.com/ (Birdie+ adds Bluetooth)
- Wearsafe — https://wearsafe.com/
