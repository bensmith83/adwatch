"""Aggregate BLE scan data into a summary payload for AI analysis."""

import hashlib
import json
import time

from adwatch.storage.base import Database


class InsightsAggregator:
    def __init__(self, db: Database):
        self._db = db

    async def build_summary(self) -> dict:
        totals = await self._get_totals()
        scan_period = await self._get_scan_period()
        by_parser = await self._get_by_parser()
        by_device_class = await self._get_by_device_class()
        top_devices = await self._get_top_devices()
        unparsed_named = await self._get_unparsed_named()
        unparsed_uuid_freq = await self._get_unparsed_uuid_freq()
        unparsed_company_freq = await self._get_unparsed_company_freq()
        recent_new = await self._get_recent_new_devices()

        return {
            "scan_period": scan_period,
            "totals": totals,
            "by_parser": by_parser,
            "by_device_class": by_device_class,
            "top_devices": top_devices,
            "unparsed_named": unparsed_named,
            "unparsed_uuid_freq": unparsed_uuid_freq,
            "unparsed_company_freq": unparsed_company_freq,
            "recent_new_devices_24h": recent_new,
        }

    async def _get_totals(self) -> dict:
        row = await self._db.fetchone(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN parsed_by IS NOT NULL THEN 1 ELSE 0 END) as parsed "
            "FROM raw_advertisements"
        )
        total = row["total"] or 0
        parsed = row["parsed"] or 0
        unparsed = total - parsed
        return {
            "total_ads": total,
            "parsed": parsed,
            "unparsed": unparsed,
            "parse_rate": round(parsed / total, 4) if total > 0 else 0,
        }

    async def _get_scan_period(self) -> dict:
        row = await self._db.fetchone(
            "SELECT MIN(first_seen) as earliest, MAX(last_seen) as latest "
            "FROM raw_advertisements"
        )
        if not row or row["earliest"] is None:
            return {"first_seen": None, "last_seen": None, "duration_hours": 0}

        earliest = row["earliest"]
        latest = row["latest"]
        duration = (latest - earliest) / 3600

        return {
            "first_seen": earliest,
            "last_seen": latest,
            "duration_hours": round(duration, 2),
        }

    async def _get_by_parser(self) -> list[dict]:
        rows = await self._db.fetchall(
            "SELECT parsed_by as parser, COUNT(*) as count, "
            "SUM(sighting_count) as sightings "
            "FROM raw_advertisements WHERE parsed_by IS NOT NULL "
            "GROUP BY parsed_by ORDER BY sightings DESC"
        )
        return [dict(r) for r in rows]

    async def _get_by_device_class(self) -> list[dict]:
        rows = await self._db.fetchall(
            "SELECT ad_type as device_class, COUNT(*) as count "
            "FROM raw_advertisements WHERE ad_type IS NOT NULL "
            "GROUP BY ad_type ORDER BY count DESC"
        )
        return [dict(r) for r in rows]

    async def _get_top_devices(self, limit: int = 20) -> list[dict]:
        rows = await self._db.fetchall(
            "SELECT ad_signature, local_name, parsed_by, ad_type, "
            "sighting_count as sightings, first_seen, last_seen "
            "FROM raw_advertisements "
            "ORDER BY sighting_count DESC LIMIT ?",
            (limit,),
        )
        results = []
        for r in rows:
            entry = {
                "identity_hash": r["ad_signature"][:16],
                "local_name": r["local_name"],
                "parser": r["parsed_by"],
                "ad_type": r["ad_type"],
                "sightings": r["sightings"],
                "first_seen": r["first_seen"],
                "last_seen": r["last_seen"],
            }
            results.append(entry)
        return results

    async def _get_unparsed_named(self, limit: int = 30) -> list[dict]:
        rows = await self._db.fetchall(
            "SELECT local_name, sighting_count as sightings, "
            "service_uuids_json, manufacturer_data_hex "
            "FROM raw_advertisements "
            "WHERE parsed_by IS NULL AND local_name IS NOT NULL "
            "ORDER BY sighting_count DESC LIMIT ?",
            (limit,),
        )
        results = []
        for r in rows:
            entry = {
                "local_name": r["local_name"],
                "sightings": r["sightings"],
            }
            if r["service_uuids_json"]:
                entry["service_uuids"] = r["service_uuids_json"]
            mfr = r["manufacturer_data_hex"]
            if mfr and len(mfr) >= 4:
                # Extract company ID (first 4 hex chars = 2 bytes LE)
                try:
                    cid = int(mfr[2:4] + mfr[0:2], 16)
                    entry["company_id"] = f"0x{cid:04X}"
                except ValueError:
                    pass
            results.append(entry)
        return results

    async def _get_unparsed_uuid_freq(self) -> list[dict]:
        rows = await self._db.fetchall(
            "SELECT service_uuids_json, COUNT(*) as count "
            "FROM raw_advertisements "
            "WHERE parsed_by IS NULL AND service_uuids_json IS NOT NULL "
            "GROUP BY service_uuids_json ORDER BY count DESC LIMIT 20"
        )
        results = []
        for r in rows:
            try:
                uuids = json.loads(r["service_uuids_json"])
                for uuid in uuids:
                    results.append({"uuid": uuid, "count": r["count"]})
            except (json.JSONDecodeError, TypeError):
                pass
        return results

    async def _get_unparsed_company_freq(self) -> list[dict]:
        rows = await self._db.fetchall(
            "SELECT manufacturer_data_hex, COUNT(*) as count "
            "FROM raw_advertisements "
            "WHERE parsed_by IS NULL AND manufacturer_data_hex IS NOT NULL "
            "AND LENGTH(manufacturer_data_hex) >= 4 "
            "GROUP BY SUBSTR(manufacturer_data_hex, 1, 4) ORDER BY count DESC LIMIT 20"
        )
        results = []
        for r in rows:
            mfr = r["manufacturer_data_hex"]
            if mfr and len(mfr) >= 4:
                try:
                    cid = int(mfr[2:4] + mfr[0:2], 16)
                    results.append({"company_id": f"0x{cid:04X}", "count": r["count"]})
                except ValueError:
                    pass
        return results

    async def _get_recent_new_devices(self) -> int:
        cutoff = time.time() - 24 * 3600
        row = await self._db.fetchone(
            "SELECT COUNT(*) as count FROM raw_advertisements "
            "WHERE first_seen >= ?",
            (cutoff,),
        )
        return row["count"] if row else 0
