"""Raw advertisement storage with deduplication."""

import hashlib
import json
import logging
import time
from datetime import datetime, timezone

from adwatch.models import Classification, RawAdvertisement
from adwatch.storage.base import Database

logger = logging.getLogger(__name__)

NULL_SENTINEL = "__null__"


class RawStorage:
    """CRUD operations for the raw_advertisements table."""

    def __init__(self, db: Database):
        self._db = db

    @staticmethod
    def _compute_signature(
        mac_address: str,
        address_type: str | None,
        manufacturer_data_hex: str | None,
        service_data_json: str | None,
        service_uuids_json: str | None,
        local_name: str | None,
    ) -> str:
        parts = f"{mac_address}|{address_type}|{manufacturer_data_hex}|{service_data_json}|{service_uuids_json}|{local_name}"
        return hashlib.sha256(parts.encode()).hexdigest()

    @staticmethod
    def _iso_to_unix(iso_timestamp: str) -> float:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.timestamp()

    async def save(
        self,
        raw: RawAdvertisement,
        classification: Classification | None = None,
        parsed_by: list[str] | None = None,
        stable_key: str | None = None,
    ) -> None:
        manufacturer_data_hex = (
            raw.manufacturer_data.hex() if raw.manufacturer_data else None
        )
        service_data_json = None
        if raw.service_data:
            service_data_json = json.dumps(
                {k: v.hex() for k, v in raw.service_data.items()}
            )
        service_uuids_json = (
            json.dumps(raw.service_uuids) if raw.service_uuids else None
        )
        parsed_by_str = ",".join(parsed_by) if parsed_by else None

        ad_type = classification.ad_type if classification else None

        if stable_key:
            ad_signature = hashlib.sha256(
                f"{raw.mac_address}|{stable_key}".encode()
            ).hexdigest()
        else:
            ad_signature = self._compute_signature(
                raw.mac_address,
                raw.address_type,
                manufacturer_data_hex,
                service_data_json,
                service_uuids_json,
                raw.local_name,
            )

        now = self._iso_to_unix(raw.timestamp)
        rssi = raw.rssi

        await self._db.execute(
            """INSERT INTO raw_advertisements
               (ad_signature, first_seen, last_seen, sighting_count,
                mac_address, address_type, manufacturer_data_hex,
                service_data_json, service_uuids_json, local_name,
                rssi_min, rssi_max, rssi_total,
                tx_power, ad_type, parsed_by)
               VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(ad_signature) DO UPDATE SET
                   last_seen = excluded.last_seen,
                   sighting_count = sighting_count + 1,
                   rssi_min = MIN(rssi_min, excluded.rssi_min),
                   rssi_max = MAX(rssi_max, excluded.rssi_max),
                   rssi_total = rssi_total + excluded.rssi_total,
                   manufacturer_data_hex = COALESCE(excluded.manufacturer_data_hex, manufacturer_data_hex),
                   service_data_json = COALESCE(excluded.service_data_json, service_data_json),
                   parsed_by = COALESCE(excluded.parsed_by, parsed_by),
                   ad_type = COALESCE(excluded.ad_type, ad_type)""",
            (
                ad_signature,
                now,
                now,
                raw.mac_address,
                raw.address_type,
                manufacturer_data_hex,
                service_data_json,
                service_uuids_json,
                raw.local_name,
                rssi,
                rssi,
                rssi,
                raw.tx_power,
                ad_type,
                parsed_by_str,
            ),
        )

    async def query(
        self,
        mac: str | None = None,
        ad_type: str | None = None,
        since: float | None = None,
        limit: int = 100,
    ) -> list[dict]:
        conditions = []
        params: list = []
        if mac:
            conditions.append("mac_address = ?")
            params.append(mac)
        if ad_type:
            conditions.append("ad_type = ?")
            params.append(ad_type)
        if since is not None:
            conditions.append("last_seen >= ?")
            params.append(since)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT *, last_seen AS timestamp, rssi_max AS rssi FROM raw_advertisements{where} ORDER BY last_seen DESC LIMIT ?"
        params.append(limit)
        return await self._db.fetchall(sql, params)

    async def get_feed(self, limit: int = 100) -> list[dict]:
        return await self._db.fetchall(
            "SELECT *, last_seen AS timestamp, rssi_max AS rssi FROM raw_advertisements ORDER BY last_seen DESC LIMIT ?",
            (limit,),
        )

    async def get_overview(self) -> dict:
        rows = await self._db.fetchall(
            "SELECT ad_type, COUNT(*) AS cnt, SUM(sighting_count) AS total_sightings "
            "FROM raw_advertisements WHERE ad_type IS NOT NULL GROUP BY ad_type"
        )
        return {
            row["ad_type"]: {"cnt": row["cnt"], "total_sightings": row["total_sightings"]}
            for row in rows
        }

    # --- Protocol Explorer methods ---

    async def explorer_query(
        self,
        ad_type: str | None = None,
        parsed_by: str | None = None,
        company_id: int | None = None,
        service_uuid: str | None = None,
        local_name: str | None = None,
        mac_prefix: str | None = None,
        min_sightings: int | None = None,
        limit: int = 100,
        group_by: str | None = None,
    ) -> list[dict]:
        if group_by == "company_id":
            sql = (
                "SELECT "
                "CASE WHEN manufacturer_data_hex IS NOT NULL AND LENGTH(manufacturer_data_hex) >= 4 "
                "THEN (UNICODE(SUBSTR(manufacturer_data_hex,3,1)) - CASE WHEN UNICODE(SUBSTR(manufacturer_data_hex,3,1)) >= 97 THEN 87 WHEN UNICODE(SUBSTR(manufacturer_data_hex,3,1)) >= 65 THEN 55 ELSE 48 END) * 16 "
                "+ (UNICODE(SUBSTR(manufacturer_data_hex,4,1)) - CASE WHEN UNICODE(SUBSTR(manufacturer_data_hex,4,1)) >= 97 THEN 87 WHEN UNICODE(SUBSTR(manufacturer_data_hex,4,1)) >= 65 THEN 55 ELSE 48 END) "
                "+ ((UNICODE(SUBSTR(manufacturer_data_hex,1,1)) - CASE WHEN UNICODE(SUBSTR(manufacturer_data_hex,1,1)) >= 97 THEN 87 WHEN UNICODE(SUBSTR(manufacturer_data_hex,1,1)) >= 65 THEN 55 ELSE 48 END) * 16 "
                "+ (UNICODE(SUBSTR(manufacturer_data_hex,2,1)) - CASE WHEN UNICODE(SUBSTR(manufacturer_data_hex,2,1)) >= 97 THEN 87 WHEN UNICODE(SUBSTR(manufacturer_data_hex,2,1)) >= 65 THEN 55 ELSE 48 END)) * 256 "
                "ELSE NULL END AS company_id_int, "
                "COUNT(*) AS count "
                "FROM raw_advertisements "
                "WHERE manufacturer_data_hex IS NOT NULL AND LENGTH(manufacturer_data_hex) >= 4 "
                "GROUP BY company_id_int"
            )
            return await self._db.fetchall(sql)

        if group_by == "ad_type":
            sql = "SELECT ad_type AS value, COUNT(*) AS count FROM raw_advertisements GROUP BY ad_type"
            return await self._db.fetchall(sql)

        conditions: list[str] = []
        params: list = []

        if ad_type == NULL_SENTINEL:
            conditions.append("ad_type IS NULL")
        elif ad_type is not None:
            conditions.append("ad_type = ?")
            params.append(ad_type)

        if parsed_by == NULL_SENTINEL:
            conditions.append("parsed_by IS NULL")
        elif parsed_by is not None:
            conditions.append("parsed_by LIKE ?")
            params.append(f"%{parsed_by}%")

        if company_id is not None:
            conditions.append(
                "manufacturer_data_hex IS NOT NULL AND LENGTH(manufacturer_data_hex) >= 4"
            )

        if service_uuid is not None:
            conditions.append("service_uuids_json LIKE ?")
            params.append(f"%{service_uuid}%")

        if local_name is not None:
            conditions.append("local_name LIKE ?")
            params.append(f"%{local_name}%")

        if mac_prefix is not None:
            conditions.append("mac_address LIKE ?")
            params.append(f"{mac_prefix}%")

        if min_sightings is not None:
            conditions.append("sighting_count >= ?")
            params.append(min_sightings)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT *, last_seen AS timestamp, rssi_max AS rssi FROM raw_advertisements{where} ORDER BY last_seen DESC LIMIT ?"
        params.append(limit)

        rows = await self._db.fetchall(sql, params)

        results = []
        for row in rows:
            row = dict(row)
            mfr_hex = row.get("manufacturer_data_hex")
            if mfr_hex and len(mfr_hex) >= 4:
                # Little-endian uint16 from first 4 hex chars
                low_byte = int(mfr_hex[0:2], 16)
                high_byte = int(mfr_hex[2:4], 16)
                cid = high_byte * 256 + low_byte
                row["company_id_int"] = cid
                row["payload_hex"] = mfr_hex[4:] if len(mfr_hex) > 4 else ""
                row["payload_length"] = len(mfr_hex) // 2
            else:
                row["company_id_int"] = None
                row["payload_hex"] = None
                row["payload_length"] = None
            results.append(row)

        # Post-filter by company_id (can't easily do in SQL)
        if company_id is not None:
            results = [r for r in results if r.get("company_id_int") == company_id]

        return results

    async def get_by_id(self, ad_id: int) -> dict | None:
        row = await self._db.fetchone(
            "SELECT *, last_seen AS timestamp, rssi_max AS rssi FROM raw_advertisements WHERE id = ?",
            (ad_id,),
        )
        return dict(row) if row else None

    async def get_facets(self) -> dict:
        ad_types = await self._db.fetchall(
            "SELECT ad_type AS value, COUNT(*) AS count FROM raw_advertisements "
            "WHERE ad_type IS NOT NULL GROUP BY ad_type ORDER BY count DESC"
        )

        # Extract company_ids from manufacturer_data_hex
        rows_with_mfr = await self._db.fetchall(
            "SELECT manufacturer_data_hex FROM raw_advertisements "
            "WHERE manufacturer_data_hex IS NOT NULL AND LENGTH(manufacturer_data_hex) >= 4"
        )
        cid_counts: dict[int, int] = {}
        for r in rows_with_mfr:
            h = r["manufacturer_data_hex"]
            low = int(h[0:2], 16)
            high = int(h[2:4], 16)
            cid = high * 256 + low
            cid_counts[cid] = cid_counts.get(cid, 0) + 1
        company_ids = [{"value": k, "count": v} for k, v in sorted(cid_counts.items(), key=lambda x: -x[1])]

        uuid_rows = await self._db.fetchall(
            "SELECT DISTINCT service_uuids_json FROM raw_advertisements "
            "WHERE service_uuids_json IS NOT NULL"
        )
        service_uuids: list[str] = []
        for r in uuid_rows:
            try:
                uuids = json.loads(r["service_uuids_json"])
                for u in uuids:
                    if u not in service_uuids:
                        service_uuids.append(u)
            except Exception:
                logger.debug("Failed to parse service_uuids_json", exc_info=True)

        local_names = await self._db.fetchall(
            "SELECT DISTINCT local_name FROM raw_advertisements "
            "WHERE local_name IS NOT NULL ORDER BY local_name LIMIT 50"
        )
        local_name_list = [r["local_name"] for r in local_names]

        return {
            "ad_types": ad_types,
            "company_ids": company_ids,
            "service_uuids": service_uuids,
            "local_names": local_name_list,
        }

    async def compare_ads(self, ids: list[int]) -> list[dict]:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = await self._db.fetchall(
            f"SELECT id, manufacturer_data_hex FROM raw_advertisements WHERE id IN ({placeholders})",
            ids,
        )
        if not rows:
            return []

        # Convert hex to byte lists
        byte_arrays = []
        for row in rows:
            h = row.get("manufacturer_data_hex")
            if h:
                byte_arrays.append(bytes.fromhex(h))
            else:
                byte_arrays.append(b"")

        max_len = max(len(b) for b in byte_arrays)
        if max_len == 0:
            return []

        result = []
        for offset in range(max_len):
            values = []
            for ba in byte_arrays:
                values.append(ba[offset] if offset < len(ba) else None)
            is_constant = len(set(v for v in values if v is not None)) <= 1 and all(v is not None for v in values)
            result.append({
                "offset": offset,
                "values": values,
                "is_constant": is_constant,
            })
        return result

    async def cleanup(self, retention_days: int, sighting_count_threshold: int = 2) -> None:
        cutoff = time.time() - (retention_days * 86400)
        await self._db.execute(
            "DELETE FROM raw_advertisements WHERE last_seen < ? AND sighting_count > ?",
            (cutoff, sighting_count_threshold),
        )
