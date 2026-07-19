# Nespresso Coffee Machine BLE Protocol

## Overview

Nespresso connected coffee machines (Vertuo, Venus/VertuoLine) advertise via BLE using company ID 0x0225 and a custom 128-bit service UUID. The BLE connection enables the Nespresso app to read capsule counts, descaling status, and brew settings.

## Identifiers

- **Company ID (SIG-registered):** `0x0225` — Nespresso France SAS
- **Company ID (on-the-wire):** `0x2502` — what shipping firmware actually
  transmits because the bytes are encoded big-endian (a spec violation).
- **Service UUID:** `06AA1910-F22A-11E3-9DAA-0002A5D5C51B` (Nespresso GATT service)
- **Local name pattern:** `{model}_{variant}_{MAC}` (e.g., `Vertuo_CV6_FCB46765786E`)
- **Device class:** `appliance`

### Byte-order quirk (important)

The BLE spec requires company-IDs to be transmitted little-endian, so an
assignment of `0x0225` should appear on the wire as `25 02`. **Every
Nespresso captured to date instead transmits `02 25`** — bytes in
big-endian order. A scanner decoding the manufacturer-data block with
spec-correct LE interpretation therefore reads the company-ID as
`0x2502`, not `0x0225`. The adwatch parser accepts both IDs to tolerate
both correct and broken implementations; in practice only `0x2502` has
ever been observed in the wild.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID (LE-decoded) | `0x2502` | Observed on every real capture |
| Company ID (intent)     | `0x0225` | Nespresso France SAS in SIG registry |
| Service UUID            | `06AA1910-...` | Nespresso app communication service |
| Local name              | `{model}_{MAC}` | Model + MAC address |

### Manufacturer Data Structure

Total: 8 bytes (2 company ID + 6 payload)

#### Examples

```
02 25 40 89 00 00 00 00   (Vertuo CV6)
02 25 00 89 00 00 00 00   (Venus)
02 25 00 09 7f e0 40 00   (Venus variant)
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0-1 | 2 | `02 25` | Company ID — big-endian-encoded 0x0225 (firmware quirk) |
| 2 | 1 | varies | Machine state (bit 6 = ready) |
| 3 | 1 | `89`/`09` | Device type / capability flags |
| 4-7 | 4 | varies | Status data (zeros on every observed capture) |

Byte 2 differs between advertisements: `40` vs `00` confirms bit 6
toggles between ready (`0x40`) and standby (`0x00`). Captures of a Venus
machine at the same address show both states cleanly. Byte 3 (`0x89`)
has been constant across every observed Vertuo / Venus machine.

### Name-less re-advertise pulses

Vertuo machines emit periodic re-advertise pulses that carry the same
manufacturer data (CID `0x0225`/`0x2502` + 6-byte payload) and the same
proprietary service UUID `06AA1910-F22A-11E3-9DAA-0002A5D5C51B`, but
**omit `localName`**. The same physical machine therefore appears in
scan logs in two forms — one with name, one without — both at the same
MAC. The adwatch parser treats a missing localName as acceptable **only
when the Vertuo proprietary UUID is also present**; CID alone is not a
sufficient signal because `0x0225` has SIG-vanity / byte-order
collisions, and the proprietary UUID alone is also not a sufficient
signal in the interest of conservative attribution. When the no-name
branch fires, the parser sets `metadata["match_mode"] =
"cid_with_vertuo_uuid"`; the name-bearing path sets `match_mode =
"name_with_cid"`.

The Vertuo proprietary UUID is itself a curiosity: it is a UUIDv1
(time-and-MAC-based) whose node bytes are `00:02:A5:D5:C5:1B`, and the
embedded timestamp resolves to roughly 2014. The exact-same node bytes
`…0002A5D5C51B` also appear on **Oura Ring**'s vendor UUID and on a
separate **TraceX-branded** vendor UUID (see
`docs/protocols/tracex-branded-device.md`; that device is currently
vendor-unattributed) — three unrelated vendors sharing one UUIDv1
node is a strong indicator the value propagated across vendors via a
shared SDK / sample-code template (likely the STMicroelectronics
BlueSTSDK reference base `XXXXXXXX-XXXX-11eX-XXXX-0002a5d5c51b`),
not that each vendor independently generated it.

The OUI `00:02:A5` has the locally-administered bit clear, so RFC 4122
says it must have originated from a real IEEE-assigned MAC on whichever
developer machine first minted these UUIDs in ~2014. Public OUI lookups
have variably attributed `00:02:A5` to Compaq Computer Corp (historical
IEEE registry entries) and STMicroelectronics (current public lookups);
the attribution is unverified and ultimately irrelevant — the node
tells you about the original developer machine, not about Nespresso's
chipset vendor.

### Local Name Patterns

| Local Name | Model | Notes |
|------------|-------|-------|
| `Vertuo_CV6_FCB46765786E` | Vertuo Next (CV6) | Last 12 chars = BLE MAC |
| `Venus_D8132A9D825A` | VertuoLine (Venus) | Original VertuoLine model |

### Known Models

| Code | Product |
|------|---------|
| CV6 | Vertuo Next |
| Venus | VertuoLine Original |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | company_id, service_uuid | Nespresso machine nearby |
| Model name | local_name prefix | Product line identification |
| Model code | local_name (e.g., CV6) | Specific model variant |
| MAC address | local_name suffix | Last 12 hex chars |
| Machine state | mfr_data byte 2 | Ready/standby/heating |

### What We Cannot Parse (requires GATT connection or Nespresso app)

- Capsule count
- Descaling status
- Brew settings
- Water tank level
- Error codes

## Identity Hashing

```
identifier = SHA256("nespresso:{mac}")[:16]
```

## Detection Significance

- Indicates a home or office kitchen environment
- Nespresso machines advertise continuously when powered on
- Multiple models may indicate a coffee enthusiast or office break room

## References

- [Nespresso](https://www.nespresso.com/) — manufacturer website
- Service UUID `06AA` base is used across the Nespresso connected range
- Bluetooth SIG company-ID registry vs vendor proprietary UUIDs: SIG
  IDs are 16-bit globally-assigned values (e.g. `0x0225` = Nespresso
  France SAS), whereas vendor UUIDs like
  `06AA1910-F22A-11E3-9DAA-0002A5D5C51B` are 128-bit values minted by
  the vendor (here, a UUIDv1 whose node bytes `…0002A5D5C51B` are
  shared across multiple unrelated vendors — see the cross-reference
  in `docs/protocols/tracex-branded-device.md`). Both are useful
  attribution signals; combining them avoids byte-order collisions
  that affect 16-bit CIDs alone.
