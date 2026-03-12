"""Protocol Specs storage layer."""

import json
import logging
import re
import time

from adwatch.storage.base import Database

logger = logging.getLogger(__name__)


_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_SPEC_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.,-]*$")


def _validate_identifier(value: str, label: str) -> None:
    if not _IDENTIFIER_RE.match(value):
        raise ValueError(f"Invalid {label}: {value!r} — must match [a-zA-Z_][a-zA-Z0-9_]*")


def _validate_spec_name(value: str) -> None:
    if not _SPEC_NAME_RE.match(value):
        raise ValueError(f"Invalid spec name: {value!r} — must start with a letter or underscore")


class SpecStorage:
    """CRUD operations for protocol_specs and protocol_spec_fields tables."""

    def __init__(self, db: Database):
        self._db = db

    async def _enable_fk(self):
        await self._db.execute("PRAGMA foreign_keys = ON")

    async def create_spec(
        self,
        name: str,
        description: str | None = None,
        company_id: int | None = None,
        service_uuid: str | None = None,
        local_name_pattern: str | None = None,
        data_source: str = "mfr",
    ) -> dict:
        _validate_spec_name(name)
        if local_name_pattern is not None:
            try:
                re.compile(local_name_pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        now = time.time()
        await self._enable_fk()
        await self._db.execute(
            """INSERT INTO protocol_specs
               (name, description, company_id, service_uuid, local_name_pattern, data_source, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, description, company_id, service_uuid, local_name_pattern, data_source, now, now),
        )
        row = await self._db.fetchone(
            "SELECT * FROM protocol_specs WHERE name = ?", (name,)
        )
        return row

    async def get_spec(self, spec_id: int) -> dict | None:
        row = await self._db.fetchone(
            "SELECT * FROM protocol_specs WHERE id = ?", (spec_id,)
        )
        if row is None:
            return None
        row["fields"] = await self.get_fields(spec_id)
        return row

    async def list_specs(self) -> list[dict]:
        return await self._db.fetchall(
            "SELECT * FROM protocol_specs ORDER BY name"
        )

    async def update_spec(self, spec_id: int, **kwargs) -> dict | None:
        existing = await self._db.fetchone(
            "SELECT * FROM protocol_specs WHERE id = ?", (spec_id,)
        )
        if existing is None:
            return None
        allowed = {"name", "description", "company_id", "service_uuid", "local_name_pattern", "data_source"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        updates["updated_at"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [spec_id]
        await self._db.execute(
            f"UPDATE protocol_specs SET {set_clause} WHERE id = ?", params
        )
        return await self._db.fetchone(
            "SELECT * FROM protocol_specs WHERE id = ?", (spec_id,)
        )

    async def delete_spec(self, spec_id: int) -> None:
        await self._enable_fk()
        await self._db.execute(
            "DELETE FROM protocol_specs WHERE id = ?", (spec_id,)
        )

    async def add_field(
        self,
        spec_id: int,
        name: str,
        offset: int,
        length: int,
        field_type: str,
        endian: str = "LE",
        description: str | None = None,
        sort_order: int = 0,
    ) -> dict:
        _validate_identifier(name, "field name")
        await self._db.execute(
            """INSERT INTO protocol_spec_fields
               (spec_id, name, offset, length, field_type, endian, description, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (spec_id, name, offset, length, field_type, endian, description, sort_order),
        )
        return await self._db.fetchone(
            "SELECT * FROM protocol_spec_fields WHERE spec_id = ? AND name = ?",
            (spec_id, name),
        )

    async def get_fields(self, spec_id: int) -> list[dict]:
        return await self._db.fetchall(
            "SELECT * FROM protocol_spec_fields WHERE spec_id = ? ORDER BY sort_order, offset",
            (spec_id,),
        )

    async def update_field(self, field_id: int, **kwargs) -> dict | None:
        existing = await self._db.fetchone(
            "SELECT * FROM protocol_spec_fields WHERE id = ?", (field_id,)
        )
        if existing is None:
            return None
        allowed = {"name", "offset", "length", "field_type", "endian", "description", "sort_order"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return existing
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [field_id]
        await self._db.execute(
            f"UPDATE protocol_spec_fields SET {set_clause} WHERE id = ?", params
        )
        return await self._db.fetchone(
            "SELECT * FROM protocol_spec_fields WHERE id = ?", (field_id,)
        )

    async def delete_field(self, field_id: int) -> None:
        await self._db.execute(
            "DELETE FROM protocol_spec_fields WHERE id = ?", (field_id,)
        )

    async def replace_fields(self, spec_id: int, fields: list[dict]) -> None:
        """Delete all existing fields for a spec and insert new ones."""
        await self._db.execute(
            "DELETE FROM protocol_spec_fields WHERE spec_id = ?", (spec_id,)
        )
        for i, f in enumerate(fields):
            await self.add_field(
                spec_id,
                name=f["name"],
                offset=f["offset"],
                length=f["length"],
                field_type=f["field_type"],
                endian=f.get("endian", "LE"),
                description=f.get("description"),
                sort_order=f.get("sort_order", i),
            )

    async def match_specs(self, ad_row: dict) -> list[dict]:
        specs = await self._db.fetchall("SELECT * FROM protocol_specs")
        matches = []
        for spec in specs:
            if self._spec_matches(spec, ad_row):
                matches.append(spec)
        return matches

    @staticmethod
    def _spec_matches(spec: dict, ad_row: dict) -> bool:
        has_criteria = False

        # Check company_id
        if spec.get("company_id") is not None:
            has_criteria = True
            mfr_hex = ad_row.get("manufacturer_data_hex")
            if mfr_hex and len(mfr_hex) >= 4:
                low = int(mfr_hex[0:2], 16)
                high = int(mfr_hex[2:4], 16)
                cid = high * 256 + low
                if cid == spec["company_id"]:
                    return True

        # Check service_uuid
        if spec.get("service_uuid") is not None:
            has_criteria = True
            uuids_json = ad_row.get("service_uuids_json")
            if uuids_json:
                try:
                    uuids = json.loads(uuids_json)
                    if spec["service_uuid"] in uuids:
                        return True
                except (json.JSONDecodeError, TypeError):
                    pass

        # Check local_name_pattern
        if spec.get("local_name_pattern") is not None:
            has_criteria = True
            local_name = ad_row.get("local_name")
            if local_name:
                try:
                    if re.search(spec["local_name_pattern"], local_name):
                        return True
                except re.error:
                    pass

        return False
