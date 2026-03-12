"""FastAPI application factory for adwatch dashboard."""

from __future__ import annotations

import pathlib

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from adwatch.dashboard.routers.explorer import create_explorer_router
from adwatch.storage.specs import SpecStorage
from adwatch.dashboard.routers.overview import create_overview_router
from adwatch.dashboard.routers.raw import create_raw_router

FRONTEND_DIR = pathlib.Path(__file__).parent / "frontend"


def create_app(raw_storage, classifier, registry, ws_manager, db=None, spec_storage=None) -> FastAPI:
    app = FastAPI(title="adwatch")

    app.include_router(create_overview_router(raw_storage, registry))
    app.include_router(create_raw_router(raw_storage))
    if spec_storage is None:
        spec_storage = SpecStorage(raw_storage._db)
    app.include_router(create_explorer_router(raw_storage, spec_storage))

    # Mount plugin API routers
    for p in registry.get_all():
        if hasattr(p.instance, "api_router"):
            router = p.instance.api_router(db)
            if router is not None:
                app.include_router(router, prefix=f"/api/{p.name}")

    @app.get("/api/parser/{name}/recent")
    async def generic_parser_recent(name: str, limit: int = Query(50, ge=1, le=500)):
        info = registry.get_by_name(name)
        if info is None:
            raise HTTPException(status_code=404, detail="Parser not found")
        if db is None:
            return []
        return await db.fetchall(
            "SELECT *, last_seen AS timestamp, rssi_max AS rssi FROM raw_advertisements WHERE ad_type = ? ORDER BY last_seen DESC LIMIT ?",
            (name, limit),
        )

    @app.put("/api/plugins/{name}/toggle")
    async def toggle_plugin(name: str):
        info = registry.get_by_name(name)
        if info is None:
            raise HTTPException(status_code=404, detail="Parser not found")
        new_state = not info.enabled
        registry.set_enabled(name, new_state)
        info = registry.get_by_name(name)
        return {
            "name": info.name,
            "description": info.description,
            "version": info.version,
            "core": info.core,
            "enabled": info.enabled,
        }

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await ws_manager.disconnect(websocket)

    if FRONTEND_DIR.exists():
        @app.get("/", response_class=HTMLResponse)
        async def index():
            return (FRONTEND_DIR / "index.html").read_text()

        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    return app
