"""Overview API endpoints: summary, feed, plugins."""

from __future__ import annotations

from fastapi import APIRouter, Query


def create_overview_router(raw_storage, registry) -> APIRouter:
    router = APIRouter()

    @router.get("/api/overview")
    async def overview():
        return await raw_storage.get_overview()

    @router.get("/api/feed")
    async def feed(limit: int = Query(100, ge=1, le=1000)):
        return await raw_storage.get_feed(limit=limit)

    @router.get("/api/plugins")
    async def plugins():
        return [
            {"name": p.name, "description": p.description, "version": p.version, "core": p.core, "enabled": p.enabled}
            for p in registry.get_all()
        ]

    @router.get("/api/plugins/ui")
    async def plugins_ui():
        import dataclasses
        from adwatch.models import PluginUIConfig, WidgetConfig
        configs = []
        for p in registry.get_all():
            if hasattr(p.instance, "ui_config"):
                cfg = p.instance.ui_config()
                if cfg is not None:
                    configs.append(dataclasses.asdict(cfg))
            else:
                # Auto-generate a generic tab for plugins without ui_config
                display_name = p.name.replace("_", " ").title()
                cfg = PluginUIConfig(
                    tab_name=display_name,
                    widgets=[
                        WidgetConfig(
                            widget_type="data_table",
                            title=f"Recent {display_name} Sightings",
                            data_endpoint=f"/api/parser/{p.name}/recent",
                            render_hints={"columns": ["timestamp", "mac_address", "rssi_max", "local_name"]},
                        ),
                    ],
                )
                configs.append(dataclasses.asdict(cfg))
        return configs

    return router
