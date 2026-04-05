"""AI Insights API endpoints."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Query

from adwatch import config
from adwatch.insights.aggregator import InsightsAggregator
from adwatch.insights.ai_client import InsightsClient
from adwatch.insights.storage import InsightsStorage

logger = logging.getLogger(__name__)


def create_insights_router(insights_storage: InsightsStorage, aggregator: InsightsAggregator) -> APIRouter:
    router = APIRouter()

    @router.get("/api/insights/config")
    async def insights_config():
        return {
            "provider": config.AI_PROVIDER,
            "has_api_key": bool(config.AI_API_KEY),
            "interval": config.INSIGHTS_INTERVAL,
            "time": config.INSIGHTS_TIME,
        }

    @router.get("/api/insights/latest")
    async def insights_latest():
        latest = await insights_storage.get_latest()
        needs_refresh = await insights_storage.should_refresh(config.INSIGHTS_INTERVAL)
        return {
            "insight": latest,
            "needs_refresh": needs_refresh,
            "has_api_key": bool(config.AI_API_KEY),
        }

    @router.post("/api/insights/generate")
    async def insights_generate():
        if not config.AI_API_KEY:
            raise HTTPException(status_code=400, detail="API key not configured. Set ADWATCH_AI_API_KEY.")

        summary = await aggregator.build_summary()
        summary_json = json.dumps(summary, default=str)

        client = InsightsClient(
            api_key=config.AI_API_KEY,
            provider=config.AI_PROVIDER,
        )
        result = await client.generate(summary)

        await insights_storage.save(
            summary_payload=summary_json,
            insight_text=result.text,
            provider=config.AI_PROVIDER,
            model=result.model,
            token_count=result.token_count,
        )

        return {
            "insight_text": result.text,
            "model": result.model,
            "token_count": result.token_count,
            "provider": config.AI_PROVIDER,
        }

    @router.get("/api/insights/history")
    async def insights_history(limit: int = Query(10, ge=1, le=50)):
        return await insights_storage.get_history(limit=limit)

    @router.get("/api/insights/payload-preview")
    async def insights_payload_preview():
        return await aggregator.build_summary()

    return router
