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

## Tracking

When new identifications emerge for any of the above, migrate the entry out
of this file into a dedicated `docs/protocols/<name>.md` and (if the protocol
is decodable) implement a plugin under `src/adwatch/plugins/`.
