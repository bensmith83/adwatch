# Unidentified BLE Beacons (Observation Log)

Captures of BLE advertisements adwatch cannot yet attribute. Documented here
so future exports + external research can close the gaps.

## W600N — Service UUID `0xFE79`

Observed 2026-04-14 01:14 UTC (9 sightings in a short burst).

| Field | Value |
|-------|-------|
| `local_name` | `W600N` |
| `service_uuids` | `["FE79"]` |
| service_data | *(empty)* |

**FE79** is *Zebra Technologies Corp* in the Bluetooth SIG registry — the
industrial barcode-scanner / handheld-terminal vendor. "W600N" doesn't match
a known Zebra SKU exactly, but Zebra's MC-series and TC-series handhelds and
the Zebra "Workforce Connect" push-to-talk radios all advertise FE79.

Best guess: an enterprise Zebra handheld radio. See `getac-barcode.md` and
`zebra.md` for related industrial devices already covered by adwatch.

## S201… — Service UUID `0x1122`

Observed continuously since 2026-04-05 (598+ sightings).

| Field | Value |
|-------|-------|
| `local_name` | `S201b91dbacb104cdC` (18 chars, mixed case with middle hex) |
| `service_uuids` | `["1122"]` |
| service_data | *(empty)* |

Service UUID `0x1122` is **not** in the Bluetooth SIG assigned-numbers
registry — it is a non-registered 16-bit UUID that the device is using
privately (technically a spec violation: only 128-bit UUIDs are allowed for
non-assigned service identifiers). Pattern `S201` + 12 hex chars + `C`
suggests the hex block is a MAC address or serial embedded in the name.

Guess: an IoT gateway / ESP32-based hobby project or a cheap tracker using
the SDK's default UUID without requesting a real one.

## OVAT5-K0194559 — Local Name Only

Observed 2026-04-18 around 17:01 UTC (6 sightings, rssi -92 dBm).

| Field | Value |
|-------|-------|
| `local_name` | `OVAT5-K0194559` |
| `service_uuids` | *(empty)* |
| `manufacturer_data` | *(empty)* |
| `service_data` | *(empty)* |
| address type | random |

The name format `OVAT5-K0194559` looks like `<model>-<serial>` where `OVAT5`
is a 5-character product code and `K0194559` is a 7-digit serial prefixed
with `K`. The ad carries no payload beyond the name (random-address
connectable beacon — likely a device waiting to be paired).

No matching SKU found in public product databases. The signal is weak
(-92 dBm max) so this was almost certainly observed as a drive-by / neighbor
and may not repeat.

**Action:** if re-observed at close range, attempt a GATT connect to read the
Device Information service (0x180A) for manufacturer / model strings.

## `uac088` — Company ID `0x5654` (unassigned)

Observed continuously through May 2026 (186 capture entries, 292 total
sightings).

| Field | Value |
|-------|-------|
| `local_name` | `uac088` (sometimes blank) |
| `manufacturer_data` | 9 bytes total — company ID `5456` LE + 7-byte payload |
| `service_uuids` | *(empty)* |
| `service_data` | *(empty)* |
| RSSI max | −86 to −94 dBm (single far-field device) |
| Distinct deviceIdentifiers | **1** (every capture is the same physical device) |

Bluetooth-SIG company ID `0x5654` is **not assigned** to any vendor in
the public registry, so this is either a private-use ID an
indie/hobbyist project picked off the shelf, or a manufacturer
shipping with a placeholder ID never properly registered. The two
bytes `54 56` are also the ASCII letters `"TV"`, which is mildly
suggestive of a television-adjacent product but proves nothing.

The string `uac088` shows up in a few places online attached to
generic ESP-Now / nRF-based BLE evaluation boards and to some
chinese-OEM HID dongles, but no canonical attribution.

### Payload Shape

Across 186 captures from the same device, the 7-byte payload contains:

```
byte 0:    0x02            constant on every capture
byte 1:    0x6A-0x88        small range (~30 distinct values)
byte 2:    0x5A-0x79        small range; `0x61` is by far the most common
byte 3:    0x5A-0x7A        small range; `0x5A` dominates
byte 4-6:  high entropy     looks essentially random across captures
```

The first three payload bytes vary smoothly over time (consistent with
a rolling counter, scaled sensor reading, or short rolling-code
window). The trailing 3 bytes have very high entropy with very few
exact-byte repeats — consistent with a per-broadcast nonce, MAC, or
encryption output. **184 of the 186 captures have a unique 9-byte
manufacturer-data string** despite all coming from one device.

That high churn rate (a new payload roughly every BLE advertisement
interval) plus the lack of a stable identity beyond the local name
makes this look like a privacy-conscious beacon (rolling identifier)
or simply an encrypted telemetry stream where the cleartext device
identity is the local name only.

### Action

- Treat `0x5654` + `uac088` as a single device fingerprint for now.
- No parser implemented — the payload structure does not yield to
  shape-fitting without a key.
- If anyone recognizes this signature, please open an issue with a
  vendor / SKU pointer and we'll migrate the entry into its own
  protocol file.

## Company ID `0x43AC` — 28-byte tag-and-nonce beacon

Observed in the 2026 adwatch export: 49 capture entries from **4
distinct devices**, every capture carrying a unique 29-byte
manufacturer-data block (no two adverts share a full payload).

| Field | Value |
|-------|-------|
| `companyID` | `0x43AC` — **not assigned** in the Bluetooth SIG registry |
| Manufacturer data | 29 bytes total (2 cid + 27 payload) |
| `local_name` | *(empty on every capture)* |
| `service_uuids` | *(empty)* |
| `service_data` | *(empty)* |
| RSSI max | −81 to −100 dBm |

### Payload Shape

```
Byte offset:  0 1 | 2 3 | 4 5 6 | 7 8 | 9 10 11 | 12 13 | 14 15 16 | 17 18 | 19 20 21 | 22 23 | 24 25 26 27 | 28
              cid   var₁   TAG-A   var₂   TAG-B   var₃    TAG-C    var₄    TAG-D    00 00     TAG-E       nonce

Constant tags (49 / 49 captures):
  TAG-A:  92 07 f1
  TAG-B:  50 65 cf
  TAG-C:  84 fa 04
  TAG-D:  16 44 2d
  TAG-E:  86 2c fc 3a   (4 bytes)

Variable pairs (always 2 bytes each):
  var₁ (byte 2-3):  ~30 distinct values, byte 2 ∈ {01,02,03,04}
  var₂ (byte 7-8):  similar
  var₃ (byte 12-13): byte 12 ∈ {01,02,03,04}
  var₄ (byte 17-18): similar

Final byte (28) varies independently — looks like a per-broadcast nonce.
```

The shape — four 3-byte fixed tokens separated by 2-byte rolling
values — is suggestive of:

- a **truncated-MAC neighbour beacon**: each TAG could be a 24-bit
  hash or partial BLE address of a nearby device, with the rolling
  pair as RSSI / age. This is roughly the shape Apple FindMy and
  some Tile / SmartTag bridges use for crowdsourced location.
- a **mesh-network proxy header**: a Bluetooth-mesh GATT proxy
  occasionally adverts a list of neighbour-hash tokens, although
  the canonical mesh format does not match this layout.
- a **vehicle Bluetooth Low Energy fingerprint broadcast**: some
  automotive BLE keys (Tesla, Polestar, GM) include their neighbour
  fingerprints to seed the relay-attack defence.

One capture additionally **bundles a SmartThings second mfr-data
block** in the same advert (`1102 1102 …`), pushing total length
past 31 bytes. That bundling is a strong hint the broadcaster is a
SmartThings-aware hub.

### Action

No parser yet. The structure is regular enough to decode once a
vendor or sibling implementation is identified. Worth chasing if
the 0x43AC company ID appears in a future SIG-registry update.

## `Nrdic67380B` / Company ID `0xFACE`

Observed: 11 capture entries from **a single device**.

| Field | Value |
|-------|-------|
| `companyID` | `0xFACE` — placeholder / private-use, often used by hobby Nordic SDK projects |
| `local_name` | `Nrdic67380B` (presumably a misspelled "Nordic" + 7-char serial) |
| Manufacturer data | 18 – 21 bytes, structured payload |
| Service data `F0C0` | `06 01 0b 38 67 e0 0b da 8f 01 68 00` (constant across captures) |

### Payload Shape

Byte 0 of the payload after `cefa` is a **packet type discriminator**:

| Type byte | Observed body shape |
|-----------|---------------------|
| `0x04` | `c4 1b c4 b6 e9 17 00 01 b2 88 12 80 24 03 d5 01 …` (looks like sensor + tag bytes) |
| `0x06` | shorter, `bc 41 8f 01 68 00 fd ff 06 01 67 00 19 00` |
| `0x07` | `c4 88 12 80 24 03 d5 01 …` plus trailing zeros (looks like a status frame) |

The 6-byte sub-sequence `88 12 80 24 03 d5` recurs across multiple
packet types — almost certainly a fixed device identifier or vendor
tag.

`0xFACE` is **not a valid Bluetooth SIG company assignment** — it
is a popular placeholder for hobbyist and Nordic SDK demo projects,
and "Nrdic67380B" looks like an off-by-one Nordic-SDK default name.

### Action

Single device, hobbyist signature, custom protocol. No parser yet —
this would only ever match the one device we saw it on.

## `Lola's E.A5.WIFI` — Verifone-style POS terminal

Observed: 2 captures, 1 device.

| Field | Value |
|-------|-------|
| `companyID` | `0x5645` — **not assigned**; the bytes spell ASCII `"VE"` (Verifone?) |
| `local_name` | `Lola's E.A5.WIFI` |
| Manufacturer data (long) | `56 45 52 15 4c 6f 6c 61 27 73 20 45 75 72 6f 70 65 61 6e 20` — ASCII reads `"VER` + `0x15 Lola's European "` |
| Manufacturer data (short) | `56 45 52 15` |

The bytes after the 2-byte company ID decode as ASCII: a literal
`"VER"` magic prefix, a `0x15` length / version byte, then a free-form
business name (`"Lola's European "` — looks like the start of "Lola's
European Cafe" or similar). One device, single location.

`Lola's` was also observed paired separately with a `SA_TMS LUX_…`
device on the same site (see below) — strongly suggesting a
**Verifone TMS (Terminal Management System) BLE pairing beacon** at
a coffee-shop POS counter.

### Action

Cool find but only one device. No parser yet — a single capture
isn't enough to confirm Verifone attribution or define a stable
schema. If a second site is captured, escalate to a real protocol
doc.

## Silicon-platform-only identifications

These captures resolve to a **silicon vendor** (the chip on the board)
but not a product vendor. Each carries enough fingerprint to recognize
the firmware base, which is useful for incident triage even without a
product attribution. None justify a dedicated parser yet — they would
either over-claim a generic SDK or apply to too many unrelated SKUs —
but we keep them documented so the silicon hint is searchable.

### `D135-XXXXXXXXXX` — Microchip / ISSC BM77 / BM78 BLE-Serial module

Two distinct devices observed, each 10-digit decimal serial suffix.

| Field | Value |
|-------|-------|
| Service UUID | `49535343-FE7D-4AE5-8FA9-9FAFD205E455` — Microchip / ISSC proprietary BLE-UART service |
| `local_name` | `D135-XXXXXXXXXX` |
| Manufacturer data | *(none)* |

The 49535343-FE7D-4AE5-… UUID is the **ISSC / Microchip BM77 + BM78
proprietary BLE-Serial / UART service** (`ISSC Technologies / Microchip
Technology Inc.`). It is **the same UUID Acaia coffee scales use** —
Microchip licenses the BM77/78 dual-mode Bluetooth module to many
unrelated downstream brands, so the UUID alone is insufficient to
identify a product line. The `D135-` naming convention narrows the
candidate pool to one product family but no public attribution has
been confirmed; possibilities include a POS / industrial scale, a
laser-distance meter, or a generic UART-over-BLE module shipped
unbranded.

References:
- Microchip BM77: https://www.microchip.com/en-us/product/bm77
- Microchip BM78: https://www.microchip.com/en-us/product/bm78

### `N-Link` — ESP32 Arduino SDK example device

One device observed, only ever advertising the standard Arduino-ESP32
example service UUID.

| Field | Value |
|-------|-------|
| `local_name` | `N-Link` |
| Service UUID | `4FAFC201-1FB5-459E-8FCC-C5C9C331914B` |
| Secondary UUID | `1FF8` (Apple Continuity overflow / accidental collision) |

The 4FAFC201-1FB5-459E-8FCC-C5C9C331914B UUID is the **default example
service UUID baked into the Arduino-ESP32 BLE library tutorials** and
appears verbatim in every "ESP32 BLE Server" sample on the internet.
"N-Link" is therefore almost certainly an ESP32 dev-kit running stock
demo code — a hobby project rather than a shipped product. No parser
written; a parser keyed on the example UUID would falsely attribute
hundreds of unrelated tutorial projects.

References:
- Random Nerd Tutorials BLE example: https://randomnerdtutorials.com/esp32-bluetooth-low-energy-ble-arduino-ide/

### `GuangJi2017` — Telink TLSR8 / TLSR9 silicon (Bluetooth-SIG 0x0211)

Five distinct devices observed advertising the local name `GuangJi2017`
with company-ID `0x0211`.

| Field | Value |
|-------|-------|
| Company ID | `0x0211` — **Telink Semiconductor Co. Ltd** (Bluetooth SIG) |
| `local_name` | `GuangJi2017` (multiple devices) |
| Manufacturer data | `11 02 11 02 …` (double-tagged Telink ID + 4-byte token) |

`0x0211` is registered to **Telink Semiconductor**, a Chinese maker of
BLE/Zigbee SoCs (TLSR825x, TLSR9 series) widely used in smart lighting
(BLE mesh), smart switches, BLE keyboards, gaming peripherals, and a
significant share of cheap Chinese smart-home gear. The `1102 1102`
manufacturer-data prefix matches Telink's BLE mesh SDK example output.

"GuangJi" is Chinese (光基 / 广济 — "Light Base" / "Wide Aid") and
likely a Chinese smart-lighting brand running on Telink silicon. The
fleet of five identically-named devices is consistent with multiple
bulbs / strips wired into a single home-mesh network.

No dedicated parser yet — too many Telink-based products would
collide on the same fingerprint. Could be migrated into a
`telink-generic.md` parser once a meaningful payload structure is
decoded.

References:
- Telink BLE Mesh wiki: https://wiki.telink-semi.cn/wiki/protocols/Bluetooth-Mesh/

## Tracking

When new identifications emerge for any of the above, migrate the entry out
of this file into a dedicated `docs/protocols/<name>.md` and (if the protocol
is decodable) implement a plugin under `src/adwatch/plugins/`.
