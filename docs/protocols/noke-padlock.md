# Noke Smart Padlock

## Overview

Noke (Nokē Inc., now part of **Janus International Group**) makes Bluetooth-controlled
smart padlocks aimed at the self-storage industry. Their **Noke 3K** ("third
generation") portable padlock is sold to operators like Public Storage,
CubeSmart, Extra Space, and StorageMart, where tenants unlock their units
via the storage operator's branded mobile app instead of carrying a key.
The locks are battery-powered, fail-secure, and report unlock events back
to the operator's cloud through the tenant's phone.

The lock advertises a short manufacturer-data blob, a vendor-defined GATT
service, and (on first generation of 3K firmware) a local name that bakes
in a stable per-unit factory ID. Unlock authentication, lock state, and
event history all live behind the vendor GATT service and are not exposed
in the advertisement.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x038B` (little-endian `8B 03`) | BT SIG-registered to **Noke** |
| Manufacturer data | `8B 03 59 19 02 00 01` / `8B 03 49 19 02 00 01` | 5-byte payload after CID; first byte varies per lock (likely state/flags), trailing 4 bytes are stable across the captured fleet |
| Service UUID | `1BC50001-0200-D29E-E511-446C609DB825` | Noke vendor-defined GATT service (not registered in BT SIG `member_uuids.yaml`) |
| Local name | `NOKE3K_<12-hex>` | e.g. `NOKE3K_C7E6B0C67538`. Only emitted by a subset of units / firmware builds; usually absent on subsequent rotations |
| Service data | (absent in observed captures) | — |
| Address type | `random` | rotating private address |
| RSSI | -91 to -101 (observed) | small padlocks at storage-corridor distance scan weakly |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Noke` |
| Product family | hard-coded | `Noke smart padlock` |
| Device class | hard-coded | `padlock` |
| Hardware generation | localName prefix | `3K` when name begins with `NOKE3K_` |
| Factory ID | localName tail | 12-hex stable per-unit ID (`C7E6B0C67538`) — survives MAC rotation |
| Vendor service UUID | `serviceUUIDs` | Presence-only |
| `state_byte_0` | manufacturer payload | First byte after CID (e.g. `0x59`, `0x49`) — likely a status / flags byte; meaning undocumented |
| `meta_bytes_1_4` | manufacturer payload | Bytes 1..4 after CID (`19020001` in captures) — stable across units, exact meaning undocumented |
| `payload_hex` | manufacturer payload | Full post-CID blob as a hex string |

### What We Cannot Parse from the Advertisement

- Lock state (locked / unlocked / open shackle / tamper).
- Battery level.
- Firmware version.
- Unlock session token / nonce.
- Event log (per-unlock history, who unlocked when).
- Decoded meaning of `state_byte_0` or `meta_bytes_1_4`.

Those all live under the `1BC50001-…` vendor GATT service and require both
a connection and Noke's proprietary characteristic map, which is not
publicly documented. The Noke mobile SDK (see references) handles all of
that as a black box, so this parser deliberately stops at "presence + stable
factory ID".

## Stable Identity

The 12-hex tail of the `NOKE3K_` local name is a per-unit factory identifier
that survives MAC rotation — multiple captures of the same physical lock
show different random MACs but the same `NOKE3K_C7E6B0C67538` name. That
makes it the right key for cross-session correlation.

```
stable_key = noke_padlock:<factory-id-lowercased>
```

The local name is only present in a fraction of observed sightings (4 of 47
in `research/nearsight_export.json`), so units that never broadcast a name
during the capture window fall back to the rotating MAC:

```
stable_key = noke_padlock:mac:<mac>
```

This is lossy — the same physical lock will appear as multiple "devices"
across address rotations when no name is ever observed — but the parser
cannot do better without the GATT-side identifiers.

## Detection Significance

- Strongly indicates a **self-storage facility**: Noke 3K is sold almost
  exclusively through the Janus / Noke self-storage channel, not as a
  retail consumer product. A cluster of Noke padlocks at one location is
  effectively a fingerprint for a Public Storage / CubeSmart / Extra Space /
  StorageMart-style operator.
- Lone Noke sightings near a residential or commercial site usually mean
  a tenant or staff member is in transit with a lock — the units are
  small and portable.
- Combined with a `random` address and a vendor service with no SIG
  registration, the shape is a typical "industrial-IoT padlock":
  presence-only without a connection.

## References

- Noke / Janus International product page — <https://www.janusintl.com/products/noke>
- Noke mobile SDK (Android) — <https://github.com/noke-inc/noke-mobile-library-android>
- Noke Core API docs — <https://github.com/noke-inc/noke-core-api-documentation>
- BT SIG `company_identifiers.yaml` — CID `0x038B` = **Noke**
- Nearsight capture: `research/nearsight_export.json` (4 distinct units, 47 sightings)
