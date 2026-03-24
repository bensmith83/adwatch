"""Raw advertisement query API."""

from __future__ import annotations

from fastapi import APIRouter, Query


def create_raw_router(raw_storage) -> APIRouter:
    router = APIRouter()

    @router.get("/api/raw")
    async def raw_query(
        mac: str | None = Query(None),
        ad_type: str | None = Query(None, alias="type"),
        since: str | None = Query(None),
        limit: int = Query(100, ge=1, le=10000),
    ):
        return await raw_storage.query(mac=mac, ad_type=ad_type, since=since, limit=limit)

    return router
