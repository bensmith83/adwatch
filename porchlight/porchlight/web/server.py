"""The page and its JSON API (SPEC §4.9).

One static HTML file plus vanilla JS that polls GET /api/state. Binds to
127.0.0.1 by default; anything wider requires web.token, given as a bearer
token or once as ?token=, which sets a cookie. POSTs must be JSON, so a
cross-site form can't drive them.
"""

from __future__ import annotations

import hmac
from pathlib import Path

from aiohttp import web

from ..engine import Engine

STATIC = Path(__file__).with_name("static")
COOKIE = "porchlight_token"
ENGINE = web.AppKey("engine", Engine)
TOKEN = web.AppKey("token", str)


def _token_ok(request: web.Request) -> bool:
    token = request.app[TOKEN]
    if not token:
        return True
    given = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        given = auth[7:].strip()
    given = given or request.query.get("token") or request.cookies.get(COOKIE)
    return given is not None and hmac.compare_digest(given.encode(), token.encode())


@web.middleware
async def auth(request: web.Request, handler):
    if not _token_ok(request):
        return web.json_response({"error": "token required"}, status=401)
    if request.method == "POST" and request.content_type != "application/json":
        return web.json_response({"error": "send JSON"}, status=415)
    response = await handler(request)
    if request.app[TOKEN] and request.query.get("token"):
        response.set_cookie(COOKIE, request.query["token"], httponly=True, samesite="Strict",
                            max_age=365 * 86400)
    return response


async def index(request: web.Request) -> web.StreamResponse:
    return web.FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


async def app_js(request: web.Request) -> web.StreamResponse:
    return web.FileResponse(STATIC / "app.js", headers={"Cache-Control": "no-cache"})


async def state(request: web.Request) -> web.Response:
    return web.json_response(request.app[ENGINE].state())


async def _body(request: web.Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        raise web.HTTPBadRequest(text="bad JSON")
    if not isinstance(body, dict):
        raise web.HTTPBadRequest(text="want a JSON object")
    return body


async def arm(request: web.Request) -> web.Response:
    engine = request.app[ENGINE]
    body = await _body(request)
    if body.get("clear_override"):
        engine.clear_override()
    elif isinstance(body.get("armed"), bool):
        engine.arm(body["armed"])
    else:
        raise web.HTTPBadRequest(text='want {"armed": true|false} or {"clear_override": true}')
    return web.json_response({"armed": engine.arming.status()})


def _int(request: web.Request, name: str) -> int:
    try:
        return int(request.match_info[name])
    except ValueError:
        raise web.HTTPNotFound()


async def ack(request: web.Request) -> web.Response:
    engine = request.app[ENGINE]
    alert_id = _int(request, "id")
    body = await _body(request)
    if alert_id not in engine.alerts.alerts:
        raise web.HTTPNotFound()
    try:
        a = engine.ack(alert_id, label=body.get("label") or None, name=str(body.get("name") or ""))
    except ValueError as e:
        raise web.HTTPBadRequest(text=str(e))
    return web.json_response(engine.alert_view(a))


async def label(request: web.Request) -> web.Response:
    engine = request.app[ENGINE]
    unit_id = _int(request, "id")
    body = await _body(request)
    if unit_id not in engine.units.units:
        raise web.HTTPNotFound()
    try:
        u = engine.label(unit_id, body.get("label") or None, str(body.get("name") or ""))
    except ValueError as e:
        raise web.HTTPBadRequest(text=str(e))
    return web.json_response(engine.unit_view(u))


async def units(request: web.Request) -> web.Response:
    return web.json_response(request.app[ENGINE].units_list(request.query.get("q", "")))


async def unit(request: web.Request) -> web.Response:
    detail = request.app[ENGINE].unit_detail(_int(request, "id"))
    if detail is None:
        raise web.HTTPNotFound()
    return web.json_response(detail)


async def rssi(request: web.Request) -> web.Response:
    trace = request.app[ENGINE].rssi_trace(_int(request, "id"))
    if trace is None:
        raise web.HTTPNotFound()
    return web.json_response(trace)


async def relearn(request: web.Request) -> web.Response:
    engine = request.app[ENGINE]
    engine.relearn()
    return web.json_response({"learning": engine.learning.status(engine.now)})


def make_app(engine: Engine, token: str = "") -> web.Application:
    app = web.Application(middlewares=[auth])
    app[ENGINE] = engine
    app[TOKEN] = token
    app.router.add_get("/", index)
    app.router.add_get("/app.js", app_js)
    app.router.add_get("/api/state", state)
    app.router.add_post("/api/arm", arm)
    app.router.add_post("/api/alerts/{id}/ack", ack)
    app.router.add_post("/api/units/{id}/label", label)
    app.router.add_get("/api/units", units)
    app.router.add_get("/api/units/{id}", unit)
    app.router.add_get("/api/units/{id}/rssi", rssi)
    app.router.add_post("/api/relearn", relearn)
    return app
