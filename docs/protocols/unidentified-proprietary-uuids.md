# Unidentified Proprietary UUID Fleets

Two device families observed in our scans use proprietary 128-bit service UUIDs whose vendors we have not been able to identify in any public registry (Bluetooth SIG, FCC ID database, [Nordic's bluetooth-numbers-database](https://github.com/NordicSemiconductor/bluetooth-numbers-database), GitHub code search, fccid.io). Both have clean local-name shapes that let us surface SKU + serial; the vendor name can be filled in later if a user reports the physical device.

These parsers exist to **stop classifying these as "unidentified beacons"** and start surfacing actionable per-unit IDs.

---

## BOSRT family

| Signal | Value |
|---|---|
| Service UUID | `6214B1A3-854C-4B2C-8054-780EB5C448B7` |
| Local name pattern | `^BOSRT([A-Z][A-Z0-9]{1,3})-?(\d{3,8})$` |
| Co-advertised service | `0x180A` (Device Information) |

Observed local names:
- `BOSRTPR7-006` → model `PR7`, unit `006` (3-digit, dash-separated; small-fleet shape)
- `BOSRTDT833059` → model `DT`, serial `833059` (6-digit, no dash; larger-fleet shape)

The `BOSRT` prefix is consistent across both — almost certainly a single vendor's SKU root. Expansion candidates considered but unconfirmed: Boston / Bosch / Bose-RealTime / Bostek; nothing matches in FCC, fccid.io, GitHub, or vendor catalogs. The co-advertised `180A` service means a GATT-connect would reveal the manufacturer name string and model number characteristic.

---

## WBB5BP family

| Signal | Value |
|---|---|
| Service UUID | `11500001-6215-11EE-8C99-0242AC120002` |
| Local name pattern | `^WBB5BP(\d{7})$` |

Observed local names: `WBB5BP0651247`, `WBB5BP0475839` — `WBB5BP` + 7-digit serial (~1M-unit address space → plausibly a high-volume health/fitness device). The `BP` substring tempts a "blood pressure" reading; the actual product is unconfirmed.

### A curious side-finding: the UUID was minted inside a Docker container

The UUID `11500001-6215-11EE-8C99-0242AC120002` decomposes as a v1 (time-based) UUID:

- **Timestamp** (`11EE-6215-11500001`) decodes to approximately **September 2023**.
- **Node bits** (`0242AC120002`) = MAC `02:42:AC:12:00:02` — the [well-known default Docker bridge `docker0` MAC](https://docs.docker.com/network/network-tutorial-standalone/).

So whoever generated this UUID did it inside a Docker container on a build server: v1 UUID generation pulls the host's primary MAC into the node bits, and a container's primary MAC is `docker0`'s default. That's a strong signal the vendor is a small-to-mid shop without an SIG vendor base UUID who minted IDs ad-hoc as part of a CI pipeline. The September-2023 timestamp probably matches a firmware build date.

This kind of MAC leakage from a UUID is occasionally written up in privacy-research contexts (see e.g. [RFC 4122 §4.5](https://datatracker.ietf.org/doc/html/rfc4122#section-4.5) on why v1 UUIDs can leak host identity); it's a small but real fingerprint of the vendor's build infrastructure.

---

## What both parsers surface

- `vendor = "unidentified"` (with notes about why we can't name it)
- The model code and/or unit serial extracted from the local name (so users can ground the entry in a physical device they own)
- The proprietary service UUID (so future investigators have a stable key to grep for)

If a user reports a physical device matching either of these signatures, the vendor field can be filled in — please file an issue with photos of the device and we'll update the parser.
