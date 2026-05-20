# Pokemon GO Plus + (HAC-039) Plugin

## Overview

The **Pokemon GO Plus +** (model `HAC-039`, also rendered "Pokemon GO Plus Plus" or "PGP+") is the 2023 second-generation Pokemon GO accessory, released **July 14, 2023** by [The Pokemon Company](https://www.pokemon.com/us/pokemon-news/get-ready-pokemon-go-plus) and [Niantic](https://www.pokemongolive.com/pokemon-go-plus-plus), and manufactured by **Hori**. Unlike the original 2016 Pokemon GO Plus (handled by the separate `pokemon_go_plus` parser), this device bridges **both** Pokemon GO **and** Pokemon Sleep — it carries a 3-axis accelerometer for sleep tracking, a speaker for Pokemon cries and alarm sounds, and a rechargeable battery (HAC-006), and uses a Nordic-class BLE radio rather than the Dialog Semi DA1458x of the original.

> **Not to be confused with the gen-1 Pokemon GO Plus.** The 2016 model uses SIG-assigned company ID `0x0553` (Niantic) and is parsed by `pokemon_go_plus` — see [`pokemon-go-plus.md`](./pokemon-go-plus.md). The two parsers are mutually exclusive: this parser rejects advertisements bearing CID `0x0553`.

The PGP+ advertises continuously over BLE behind an **unregistered pseudo-company-ID `0xA00C`** (not SIG-assigned — vendor magic) and exposes a custom 128-bit service UUID `21c50462-67cb-63a3-5c4c-82b5b9939aef` in the advertised service-data dictionary. The 32-bit short form `21C50462` is what CoreBluetooth surfaces as the service-data key in captured scans, and it is the same UUID family Dialog Semi reserves for SUOTA (over-the-air firmware update) on DA1458x silicon — Niantic and Hori reused the prefix even though the radio class differs from gen-1.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Pseudo company ID | `0xA00C` (**unregistered** with SIG) | LE wire bytes `0c a0`; vendor magic only |
| Service-data UUID | `21C50462` (short) / `21c50462-67cb-63a3-5c4c-82b5b9939aef` (long) | Present on every PGP+ sighting in our captures |
| Local name | `Pokemon GO Plus` | Same string the gen-1 used — **not** a distinguishing signal on its own |
| Address type | random (rotates) | Surfaced as `addressType=random` in CoreBluetooth |

The 32-bit `21C50462` UUID is the **anchor signal**: every captured PGP+ advertisement carries it, even units that omit the manufacturer-data payload entirely. The unregistered pseudo-CID `0xA00C` paired with the `"Pokemon GO Plus"` local name is the **fallback signal** for revisions that don't include service data.

### Manufacturer Data Layout (when present — 17 bytes)

```
Bytes 0..1   : 0c a0                       ← LE pseudo-company-ID 0xA00C
Bytes 2..8   : 44 20 32 35 30 31 32        ← ASCII "D 25012" — fixed signature
Byte  9      : XX                          ← per-unit byte (0x76, 0x42 observed)
Bytes 10..16 : 1b 16 e9 b6 98 00 00        ← fixed 7-byte tail
```

The fixed `"D 25012"` ASCII fragment is the most reliable wire fingerprint — it appears bytes 2..8 of every captured payload. The single varying byte at offset 9 differs between physical units (likely a per-device serial nibble or production batch tag), and the trailing 7 bytes are constant across all captures. None of the bytes appear to encode runtime state (battery, connection, button press) — the advertisement looks like a static identity beacon.

Some PGP+ units advertise **without** manufacturer data, exposing only the `21C50462` service-data UUID plus the local name. Both forms must be recognised; the parser uses an OR match.

### Stable Key

We use `pokemon_go_plus_plus:<macAddress>` as the stable key. The PGP+ uses a rotating random BD_ADDR so the key is per-sighting rather than per-device; cross-rotation collapse would require correlating the per-unit byte at offset 9 across captures and is left to a future revision.

## Detection Significance

- **Active Pokemon GO / Pokemon Sleep user nearby.** PGP+ owners tend to wear the device 24/7 (it's the only Pokemon Sleep companion hardware), so a sighting is informative for both occupancy and gamer identification.
- **One device per person.** The PGP+ pairs to a single account; aggregated sightings track an individual rather than a household.
- **Distinguishes gen-2 from gen-1.** Crowds at Pokemon GO events sometimes mix both generations; this parser plus `pokemon_go_plus` together let us count them separately.

## What We Cannot Parse from Advertisements

- **Sleep state / accelerometer data.** Sleep tracking telemetry is transferred over GATT only when paired with Pokemon Sleep, not advertised.
- **Battery / charge state.** Not surfaced in the advertisement.
- **Catch / spin events.** GATT only.
- **Per-unit serial.** Byte 9 of the manufacturer payload varies but we have not correlated it with the printed serial on the housing.

## References

- [Get Ready: Pokemon GO Plus + announcement (pokemon.com)](https://www.pokemon.com/us/pokemon-news/get-ready-pokemon-go-plus)
- [Pokemon GO Plus + product page (pokemongolive.com)](https://www.pokemongolive.com/pokemon-go-plus-plus)
- [Pokemon GO Plus + Technical FAQs (Pokemon Support)](https://support.pokemon.com/hc/en-us/articles/16894757699988-Pok%C3%A9mon-GO-Plus-Technical-FAQs)
- [Pokemon GO Plus + Manual (Nintendo EU PDF)](https://www.nintendo.com/eu/media/downloads/support_1/nintendoswitch/NSwitch_Information_PokemonGoPlus_Manual.pdf)
- [Pokemon GO Plus +: release date & differences (Dexerto)](https://www.dexerto.com/pokemon/what-is-the-pokemon-go-plus-plus-device-2201364/) — independent confirmation of July 14, 2023 release and Hori as OEM
- [seansegal/PokemonGoPlusPlus](https://github.com/seansegal/PokemonGoPlusPlus) — homebrew sleep-tracker probe documenting the `21c50462-...` service UUID family
- [coderjesus.com — Hacking the Pokemon Go Plus Over-the-Air](https://coderjesus.com/blog/pgp-suota/) — documents the `21c50462-67cb-63a3-5c4c-82b5b9939aef` SUOTA attribute, reused from the Dialog Semi DA1458x SDK on gen-1
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — confirms `0xA00C` is not SIG-assigned
