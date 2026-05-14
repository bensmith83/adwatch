# Sensi Smart Thermostat (Emerson / Copeland)

## Overview

Sensi is Emerson's line of consumer Wi-Fi smart thermostats (now sold
under the Copeland brand after Emerson spun off its Climate
Technologies division). They advertise over BLE while in setup /
re-configuration mode so the official Sensi mobile app can discover
and provision them onto the home Wi-Fi network. Once provisioned,
day-to-day control happens over Wi-Fi → cloud, but the BLE advertiser
is left running and remains visible to passive scanners.

The advertisement is short and fixed — it identifies the unit but
does not expose temperature, humidity, or schedule data over BLE. The
parser extracts the model-ID suffix (a per-device identifier visible
in the local name) and a stable per-device hash.

## Supported Models

Sensi thermostats observed in the wild advertising this profile:

| Local Name pattern              | Family                       |
|---------------------------------|------------------------------|
| `Smart Thermostat-XXXX`         | Sensi Touch / Touch 2 / 1F87U-42WFC |
| `Smart Thermostat-XXXXXX`       | Newer Sensi Touch 2 firmware |

`XXXX` (or up to 8 chars) is a hex tag derived from the unit's
internal serial number. It is **stable across factory resets** for
the same physical unit (verified via repeated captures over weeks)
and survives BLE MAC rotation, so it is the right primary identifier.

## BLE Advertisement Format

### Identification

Three independent signals make detection robust:

1. **Local name** must match `^Smart Thermostat-[0-9A-Fa-f]{4,8}$`
2. **Service UUID** `2141E110-213A-11E6-B67B-9E71128CAE77` — Sensi's
   private 128-bit service UUID (UUIDv1, time field decodes to
   May 2016, matching the Sensi Touch product launch window).
3. **Company ID** `0x0093` — Emerson Electric Co. in the Bluetooth
   SIG company-ID registry.

The parser requires **(1)** plus **at least one of (2) or (3)** so
unrelated devices that happen to be locally named "Smart Thermostat-…"
don't get attributed to Sensi.

### Manufacturer Data Layout

```
Offset  Bytes        Meaning
  0-1   93 00        Company ID 0x0093 (Emerson Electric, little-endian)
  2     00           Reserved / status nibble (always 0x00 observed)
  3     XX           Status byte (most commonly 0xE0; high nibble varies)
```

The payload is 4 bytes total — there is **no measured data in the BLE
broadcast**. The trailing `0xE0` byte is suspected to encode pairing /
discoverability flags (cloud-paired devices alternate with 0xC0 /
0xE0 patterns) but this has not been definitively decoded; the
parser preserves it in `payload_hex` for forensic inspection.

### Service Data

None observed — the Sensi service UUID is advertised but service-data
bytes are not populated. Telemetry flows over Wi-Fi to the Sensi
cloud, not over BLE.

## Identity Hashing

```
identifier_hash = SHA256("sensi_thermostat:{local_name}")[:16]
```

- Survives MAC rotation (which Sensi performs every ~15 minutes when
  the unit is on battery backup).
- The model-ID suffix in the local name is the stable per-unit token.

## What We Cannot Parse

- Current setpoint or measured indoor temperature
- HVAC mode (heat / cool / auto)
- Battery level for battery-backed units
- Schedule program

All telemetry requires Wi-Fi/cloud access or a connected GATT session.

## References

- Sensi product line: https://sensi.emerson.com/
- 1F87U-42WFC FCC filing (radio specifics): https://fccid.io/SZV-1F87U42WFC
- Bluetooth SIG company-ID 0x0093 → Emerson Electric Co.
