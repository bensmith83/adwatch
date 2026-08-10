# Epson Printer Setup Beacon — Numeric Model Code (`CID 0x0040`)

## Overview

Epson EcoTank and WorkForce inkjet printers advertise a BLE **setup beacon** so the Epson Smart Panel app can find them during onboarding. Two advertisement shapes exist, and this document covers the second one.

The **named** shape carries a self-identifying local name (`ET-2800 Series`, `WF-2950 Series`) and is already handled by [`EpsonEcoTankParser`](../../Sources/Parsers/EpsonEcoTankParser.swift) and [`EpsonWorkForceParser`](../../Sources/Parsers/EpsonWorkForceParser.swift).

The **nameless** shape carries no local name at all — just the company ID, the setup-service UUID, and a 5-byte manufacturer frame. Both named parsers require the name, so nameless frames fell through unparsed.

They need not: the nameless frame contains a **numeric model code** that resolves to the exact printer model. The 2026-07-31 NearSight telemetry sweep captured 34 records carrying an Epson setup UUID; 15 also carried a `<model> Series` name, and those 15 give a contradiction-free code→model table. The remaining 19 nameless frames can be resolved from it.

## Supported Models

Codes attested by a same-corpus sighting that also carried the self-identifying name:

| Model code (LE16) | Model | Product line | Named sightings |
|-------------------|-------|--------------|-----------------|
| 602 | WF-3820 | WorkForce | 1 |
| 616 | ET-4850 | EcoTank | 1 |
| 617 | ET-3850 | EcoTank | 1 |
| 620 | ET-2800 | EcoTank | 6 |
| 621 | ET-2400 | EcoTank | 2 |
| 651 | ET-2850 | EcoTank | 1 |
| 692 | WF-2950 | WorkForce | 2 |
| 705 | ET-4810 | EcoTank | 1 |
| 811 | ET-2980 | EcoTank | 1 |

No code ever appeared with two different models, and no model with two different codes.

Codes seen only on nameless frames, therefore **unresolved**: `689` (7 records), `809` (1 record).

**The code is not a formula.** 620 → ET-2800 but 621 → ET-2400; 811 → ET-2980 but 809 → unknown. It is an internal product index, so this table can only ever grow from real labelled captures — never be extrapolated.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0040` | SIG-assigned to **Seiko Epson Corporation** |
| Manufacturer-data length | exactly 5 bytes | 34/34 corpus records |
| Manufacturer-data byte [2] | `0x00` | Reserved; 34/34 |
| Service UUID | `802A0000-4EF4-4E59-B573-2BED4A4AC159` or `…AC158` | Epson printer setup service |
| Local name | absent (nameless shape) | Named shape belongs to the two existing parsers |
| Address type | random | Rotates |

Requiring the setup UUID **and** the CID gives two independent signals; the CID alone would be too weak a gate on a shared vendor slot.

### Wire Layout

```
40 00 | 00 | CC CC
\__ _/  \_/  \_ _/
   \/    |     \/
 LE CID  |   model code, little-endian uint16
 0x0040  reserved (always 0x00)
```

Real captures:

```
40 00 00 6c 02   ->  code 620  ->  ET-2800
40 00 00 6d 02   ->  code 621  ->  ET-2400
40 00 00 5a 02   ->  code 602  ->  WF-3820
40 00 00 b4 02   ->  code 692  ->  WF-2950
40 00 00 2b 03   ->  code 811  ->  ET-2980
40 00 00 b1 02   ->  code 689  ->  (unresolved)
```

### The setup UUID does NOT identify the product line

`EpsonWorkForceParser`'s header notes that WorkForce uses `…AC158` while EcoTank uses `…AC159`. In real captures that separation does not hold: of the three named WorkForce records in this corpus, **two advertise `…AC159`** (the "EcoTank" UUID) and only one advertises `…AC158`.

| Service UUID | Named EcoTank | Named WorkForce | Nameless |
|--------------|---------------|-----------------|----------|
| `…AC159` | 12 | 2 | 18 |
| `…AC158` | 0 | 1 | 1 |

The product line must therefore come from the **model code**, not the UUID. The parser accepts both UUIDs as routing keys and records which one was actually seen as `setup_service`, without inferring the line from it.

## Parser Scope (Passive Only)

The parser accepts a frame when CID `0x0040` is present, the manufacturer data is exactly 5 bytes with byte [2] `= 0x00`, and one of the two Epson setup UUIDs is advertised. It reports:

- vendor (`Seiko Epson Corporation`) and CID
- `model_code` (the raw LE16), always
- `model` + `product_line` + `model_resolved=true` when the code is in the attested table
- `model_resolved=false` plus an explicit note when it is not — the code is reported raw, never guessed

It **yields to the named parsers**: if the local name matches `^(ET|WF)-\d{3,4} Series$` the parser returns `nil`, so named frames keep their existing single-parser result and this parser only ever fills the gap. An unrelated local name (a user-renamed printer) is still accepted — the frame shape, not the absence of a name, is the subject.

### What we cannot parse

Ink levels, job state, error conditions, and the printer's serial number are not in the advertisement — they require a GATT connection or the Epson Smart Panel app's own protocol. The beacon carries model identity and presence, nothing more.

## Stable Identity

Identity keys on the BLE address:

```
identifierHash = sha256_16("epson_printer_model_beacon:<mac>")
stableKey      = nil
```

The model code **must not** become the identity. It identifies a *model*, not a *unit* — two ET-2800s in range would otherwise collapse into a single device.

## Detection Significance

- **Model resolution without a name.** This is the rare case where an anonymous frame yields an exact SKU, because the vendor's own named frames provided the labels. It is a good template: when a device alternates between a named and a nameless advertisement, the named one can be mined for a lookup table that unlocks the other.
- **Printers are stationary infrastructure.** An Epson setup beacon is a reliable home/office anchor. It also indicates a printer that was never fully onboarded or that keeps its setup radio on.
- **Table growth is the maintenance cost.** Two codes (689, 809) are already unresolved. Each future sweep should re-run the named/nameless correlation and extend the table with any newly labelled codes.

## References

- [Bluetooth SIG company identifiers (canonical YAML)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — `0x0040 = Seiko Epson Corporation`; verified locally 2026-07-31.
- [`Sources/Parsers/EpsonEcoTankParser.swift`](../../Sources/Parsers/EpsonEcoTankParser.swift) — named EcoTank frame, origin of the `…AC159` UUID.
- [`Sources/Parsers/EpsonWorkForceParser.swift`](../../Sources/Parsers/EpsonWorkForceParser.swift) — named WorkForce frame, origin of the `…AC158` UUID.
- `research/sweep-2026-07-31-candidates.md` (NearSight app repo) — full per-record evidence table for the code→model correlation.
