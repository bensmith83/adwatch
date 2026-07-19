# Suunto Movesense (Open Wearable Sensor Platform)

## Overview

**Movesense** is **Suunto Oy**'s open wearable sensor platform — small,
hackable BLE sensor modules (HR / IMU / ECG / temperature) used in
medical research, sports research, occupational safety, livestock
tracking, and as the BLE backbone for **Suunto Smart Belts** and a
range of third-party OEM wearables. Suunto publishes a full
GATT-RPC framework called **Whiteboard** so developers can call any
sensor function over BLE.

This parser is **double-confirmed**: both signals point to the same
vendor, so a frame with either is a high-confidence Suunto match.

| Signal | Value | Source |
|---|---|---|
| Company ID | `0x009F` | BT SIG `company_identifiers.yaml` → Suunto Oy |
| Service UUID | `61353090-8231-49CC-B57A-886370740041` | Movesense Whiteboard API reference (`{0x41,0x00,...,0x61}` byte array, little-endian byte representation of the same UUID) |

When both signals are present in one frame, the parser tags
`signal_path = "cid_and_uuid"`. When only the UUID appears (scan-
response split), it tags `uuid_only`. When only the CID appears
(sibling Suunto products like Ambit/9/Vertical/Ocean GPS watches that
don't expose Whiteboard), it demotes `product` to "Suunto BLE device
(generic)" with `cid_only`.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| CID | `0x009F` | Suunto Oy — SIG-registered |
| Service UUID | `61353090-8231-49CC-B57A-886370740041` | Movesense Whiteboard service |
| Local name | `Movesense <6-16 digit serial>` (optional) | e.g. `Movesense 174030000113` |
| Address type | `random` | rotating BD_ADDR |

### What We Can Surface

| Field | Source | Notes |
|---|---|---|
| Vendor | hard-coded | `Suunto Oy` |
| Product | UUID presence | `Movesense` when Whiteboard UUID present; otherwise `Suunto BLE device (generic)` |
| `signal_path` | derived | `cid_and_uuid` / `uuid_only` / `cid_only` |
| `whiteboard_uuid` | hard-coded | when UUID present |
| `local_name` | localName | when present |
| `sensor_serial` | localName regex | numeric serial after `Movesense ` |

### What We Cannot Surface from the Advertisement

- Specific Movesense model variant (HR2, MD, OEM-branded).
- Live sensor data (HR, IMU motion, ECG waveform, temperature) —
  these are accessed via Whiteboard GATT calls post-connect.
- Firmware revision / app version.
- Subject / wearer identity.
- Recording state (data being streamed vs cached).

## Stable Identity

The numeric serial (when present in localName) is the stable per-unit
anchor — it's printed on the Movesense module and persists across
BD_ADDR rotation:

```
stable_key = suunto_movesense:serial:<digits>     (preferred)
stable_key = suunto_movesense:mac:<bd_addr>       (fallback when nameless)
identifier = SHA256(stable_key)[:16]
```

## Detection Significance

- Movesense modules are most commonly deployed in **clinical / sports
  research** (university labs, sports-science labs, hospitals), in
  **insurance** and **occupational safety** contexts (fatigue
  monitoring), and embedded in third-party wearables. Presence often
  implies a research participant or a fitness/medical use case rather
  than a typical consumer device.
- Sibling SIG UUIDs we DON'T match here: Suunto consumer GPS watches
  (Ambit, 9, Vertical, Ocean) use a different proprietary protocol;
  the CID-only path is conservative about claiming Movesense for those.

## References

- [BT SIG `company_identifiers.yaml`](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — confirms `0x009F` → Suunto Oy
- [Movesense API reference (Whiteboard UUID byte array documented)](https://www.movesense.com/docs/esw/api_reference/)
- [Movesense platform site](https://www.movesense.com/)
- [Suunto Movesense product page](https://www.suunto.com/sports/Movesense-by-suunto/)
