"""FastAPI application factory for adwatch dashboard."""

from __future__ import annotations

import asyncio
import json
import logging
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from adwatch import config
from adwatch.dashboard.routers.explorer import create_explorer_router
from adwatch.dashboard.routers.insights import create_insights_router
from adwatch.dashboard.routers.overview import create_overview_router
from adwatch.dashboard.routers.raw import create_raw_router
from adwatch.insights.aggregator import InsightsAggregator
from adwatch.insights.ai_client import InsightsClient
from adwatch.insights.storage import InsightsStorage
from adwatch.storage.specs import SpecStorage

logger = logging.getLogger(__name__)

FRONTEND_DIR = pathlib.Path(__file__).parent / "frontend"


async def _insights_auto_refresh(insights_storage: InsightsStorage, aggregator: InsightsAggregator):
    """Background task that periodically generates AI insights."""
    await asyncio.sleep(30)  # Wait for app to settle
    while True:
        try:
            if config.AI_API_KEY and config.INSIGHTS_INTERVAL != "manual":
                if await insights_storage.should_refresh(config.INSIGHTS_INTERVAL):
                    logger.info("Auto-generating AI insights...")
                    summary = await aggregator.build_summary()
                    client = InsightsClient(api_key=config.AI_API_KEY, provider=config.AI_PROVIDER)
                    result = await client.generate(summary)
                    await insights_storage.save(
                        summary_payload=json.dumps(summary, default=str),
                        insight_text=result.text,
                        provider=config.AI_PROVIDER,
                        model=result.model,
                        token_count=result.token_count,
                    )
                    logger.info("AI insights generated (%d tokens)", result.token_count)
        except Exception:
            logger.exception("Failed to auto-generate insights")
        await asyncio.sleep(300)  # Check every 5 minutes


def create_app(raw_storage, classifier, registry, ws_manager, db=None, spec_storage=None) -> FastAPI:
    # Mutable container so lifespan closure can see values set later
    _insights = {"storage": None, "aggregator": None}

    @asynccontextmanager
    async def lifespan(app):
        task = None
        if _insights["storage"] and _insights["aggregator"]:
            task = asyncio.create_task(
                _insights_auto_refresh(_insights["storage"], _insights["aggregator"])
            )
        yield
        if task and not task.done():
            task.cancel()

    app = FastAPI(title="adwatch", lifespan=lifespan)

    app.include_router(create_overview_router(raw_storage, registry))
    app.include_router(create_raw_router(raw_storage))
    if spec_storage is None and db is not None:
        spec_storage = SpecStorage(db)
    app.include_router(create_explorer_router(raw_storage, spec_storage))

    # AI Insights
    if db is not None:
        _insights["storage"] = InsightsStorage(db)
        _insights["aggregator"] = InsightsAggregator(db)
        app.include_router(create_insights_router(_insights["storage"], _insights["aggregator"]))

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
