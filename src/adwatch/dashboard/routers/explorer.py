"""Protocol Explorer API."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from adwatch.vendors import bt_company_name, oui_vendor, best_vendor


class CreateSpecRequest(BaseModel):
    name: str
    description: Optional[str] = None
    company_id: Optional[int] = None
    service_uuid: Optional[str] = None
    local_name_pattern: Optional[str] = None
    data_source: str = "mfr"
    fields: Optional[list[dict]] = None


class UpdateSpecRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    company_id: Optional[int] = None
    service_uuid: Optional[str] = None
    local_name_pattern: Optional[str] = None
    data_source: Optional[str] = None
    fields: Optional[list[dict]] = None


class AddFieldRequest(BaseModel):
    name: str
    offset: int
    length: int
    field_type: str
    endian: str = "LE"
    description: Optional[str] = None
    sort_order: int = 0


class UpdateFieldRequest(BaseModel):
    name: Optional[str] = None
    offset: Optional[int] = None
    length: Optional[int] = None
    field_type: Optional[str] = None
    endian: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


def _enrich_vendor(row: dict) -> dict:
    """Add vendor lookup fields to an ad row."""
    cid = row.get("company_id_int")
    mac = row.get("mac_address")
    addr_type = row.get("address_type")

    # Derive company_id_int if not already present (detail endpoint)
    if cid is None:
        mfr_hex = row.get("manufacturer_data_hex")
        if mfr_hex and len(mfr_hex) >= 4:
            low = int(mfr_hex[0:2], 16)
            high = int(mfr_hex[2:4], 16)
            cid = high * 256 + low

    bt_name = bt_company_name(cid)
    oui_name = oui_vendor(mac) if addr_type and "random" not in addr_type else None
    row["bt_company_name"] = bt_name
    row["oui_vendor"] = oui_name
    row["vendor_name"] = best_vendor(mac, addr_type, cid)
    return row


def create_explorer_router(raw_storage, spec_storage=None) -> APIRouter:
    router = APIRouter()

    # --- Spec CRUD endpoints ---

    if spec_storage is not None:
        @router.post("/api/explorer/specs")
        async def create_spec(body: CreateSpecRequest):
            try:
                spec = await spec_storage.create_spec(
                    name=body.name,
                    description=body.description,
                    company_id=body.company_id,
                    service_uuid=body.service_uuid,
                    local_name_pattern=body.local_name_pattern,
                    data_source=body.data_source,
                )
                if body.fields:
                    for i, f in enumerate(body.fields):
                        await spec_storage.add_field(
                            spec["id"],
                            name=f["name"],
                            offset=f["offset"],
                            length=f["length"],
                            field_type=f["field_type"],
                            endian=f.get("endian", "LE"),
                            description=f.get("description"),
                            sort_order=f.get("sort_order", i),
                        )
                    spec = await spec_storage.get_spec(spec["id"])
                return spec
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                if "UNIQUE" in str(e):
                    raise HTTPException(status_code=409, detail="Spec name already exists")
                raise

        @router.get("/api/explorer/specs")
        async def list_specs():
            return await spec_storage.list_specs()

        @router.get("/api/explorer/specs/{spec_id}")
        async def get_spec(spec_id: int):
            spec = await spec_storage.get_spec(spec_id)
            if spec is None:
                raise HTTPException(status_code=404, detail="Spec not found")
            return spec

        @router.put("/api/explorer/specs/{spec_id}")
        async def update_spec(spec_id: int, body: UpdateSpecRequest):
            updates = {k: v for k, v in body.model_dump().items() if v is not None and k != "fields"}
            fields = body.fields
            result = await spec_storage.update_spec(spec_id, **updates)
            if result is None:
                raise HTTPException(status_code=404, detail="Spec not found")
            if fields is not None:
                await spec_storage.replace_fields(spec_id, fields)
            return await spec_storage.get_spec(spec_id)

        @router.delete("/api/explorer/specs/{spec_id}")
        async def delete_spec(spec_id: int):
            spec = await spec_storage.get_spec(spec_id)
            if spec is None:
                raise HTTPException(status_code=404, detail="Spec not found")
            await spec_storage.delete_spec(spec_id)
            return {"ok": True}

        @router.post("/api/explorer/specs/{spec_id}/fields")
        async def add_field(spec_id: int, body: AddFieldRequest):
            spec = await spec_storage.get_spec(spec_id)
            if spec is None:
                raise HTTPException(status_code=404, detail="Spec not found")
            field = await spec_storage.add_field(
                spec_id,
                name=body.name,
                offset=body.offset,
                length=body.length,
                field_type=body.field_type,
                endian=body.endian,
                description=body.description,
                sort_order=body.sort_order,
            )
            return field

        @router.put("/api/explorer/specs/{spec_id}/fields/{field_id}")
        async def update_field(spec_id: int, field_id: int, body: UpdateFieldRequest):
            updates = {k: v for k, v in body.model_dump().items() if v is not None}
            result = await spec_storage.update_field(field_id, **updates)
            if result is None:
                raise HTTPException(status_code=404, detail="Field not found")
            return result

        @router.delete("/api/explorer/specs/{spec_id}/fields/{field_id}")
        async def delete_field(spec_id: int, field_id: int):
            existing = await spec_storage.get_field(field_id)
            if existing is None:
                raise HTTPException(status_code=404, detail="Field not found")
            await spec_storage.delete_field(field_id)
            return {"ok": True}

        @router.get("/api/explorer/ad/{ad_id}/specs")
        async def matching_specs(ad_id: int):
            ad_row = await raw_storage.get_by_id(ad_id)
            if ad_row is None:
                raise HTTPException(status_code=404, detail="Ad not found")
            return await spec_storage.match_specs(ad_row)

        @router.get("/api/explorer/specs/{spec_id}/codegen")
        async def codegen(spec_id: int):
            spec = await spec_storage.get_spec(spec_id)
            if spec is None:
                raise HTTPException(status_code=404, detail="Spec not found")
            from adwatch.codegen import generate_parser
            code = generate_parser(spec)
            return {"code": code}

    @router.get("/api/explorer/ads")
    async def explorer_ads(
        ad_type: str | None = Query(None),
        parsed_by: str | None = Query(None),
        company_id: int | None = Query(None),
        service_uuid: str | None = Query(None),
        local_name: str | None = Query(None),
        mac_prefix: str | None = Query(None),
        min_sightings: int | None = Query(None),
        limit: int = Query(100, ge=1, le=10000),
        group_by: str | None = Query(None),
    ):
        results = await raw_storage.explorer_query(
            ad_type=ad_type,
            parsed_by=parsed_by,
            company_id=company_id,
            service_uuid=service_uuid,
            local_name=local_name,
            mac_prefix=mac_prefix,
            min_sightings=min_sightings,
            limit=limit,
            group_by=group_by,
        )
        return [_enrich_vendor(r) for r in results]

    @router.get("/api/explorer/ad/{ad_id}")
    async def explorer_ad_detail(ad_id: int):
        row = await raw_storage.get_by_id(ad_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Ad not found")
        return _enrich_vendor(row)

    @router.get("/api/explorer/facets")
    async def explorer_facets():
        facets = await raw_storage.get_facets()
        for cid_entry in facets.get("company_ids", []):
            cid_entry["name"] = bt_company_name(cid_entry["value"])
        return facets

    @router.get("/api/explorer/compare")
    async def explorer_compare(ids: str = Query(...)):
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
        return await raw_storage.compare_ads(id_list)

    return router
