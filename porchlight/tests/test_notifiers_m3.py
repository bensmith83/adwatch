import asyncio
import json

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from porchlight.config import Notify
from porchlight.notify import build_notifiers
from porchlight.notify.mqtt import MqttNotifier
from porchlight.notify.ntfy import NtfyNotifier
from porchlight.notify.webhook import WebhookNotifier


def alert(severity="alert"):
    return {"id": 7, "rule": "R1", "severity": severity, "created": 1760000000.0, "title": "Lingering stranger",
            "message": "Watch (Acme; Serial; …0001) has been near for 12 min", "unit": {"hint": "0001"}}


class Http:
    def __init__(self, status=200):
        self.requests = []
        self.status = status

    async def handler(self, request):
        self.requests.append((request.method, request.path, dict(request.headers), await request.read()))
        return web.Response(status=self.status, text="ok")

    async def __aenter__(self):
        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", self.handler)
        self.server = TestServer(app)
        await self.server.start_server()
        return self

    async def __aexit__(self, *exc):
        await self.server.close()

    def url(self, path):
        return str(self.server.make_url(path))


# --- ntfy -------------------------------------------------------------------------

async def test_ntfy_posts_the_message_with_title_priority_and_token():
    async with Http() as h:
        n = NtfyNotifier(Notify(type="ntfy", options={"url": h.url("/porch-topic"), "token": "tk_test"}))
        await n.send(alert())
        await n.close()
    (method, path, headers, body) = h.requests[0]
    assert method == "POST" and path == "/porch-topic"
    assert body.decode() == alert()["message"]
    assert headers["Title"] == "Lingering stranger"
    assert headers["Priority"] == "high"
    assert headers["Authorization"] == "Bearer tk_test"


async def test_ntfy_warn_is_default_priority_and_no_token_means_no_auth():
    async with Http() as h:
        n = NtfyNotifier(Notify(type="ntfy", options={"url": h.url("/t")}))
        await n.send(alert("warn"))
        await n.close()
    headers = h.requests[0][2]
    assert headers["Priority"] == "default"
    assert "Authorization" not in headers


async def test_ntfy_raises_on_http_errors():
    async with Http(status=500) as h:
        n = NtfyNotifier(Notify(type="ntfy", options={"url": h.url("/t")}))
        with pytest.raises(Exception):
            await n.send(alert())
        await n.close()


def test_ntfy_needs_a_url():
    with pytest.raises(ValueError, match="url"):
        NtfyNotifier(Notify(type="ntfy"))


# --- webhook ------------------------------------------------------------------------

async def test_webhook_posts_the_alert_json():
    async with Http() as h:
        n = WebhookNotifier(Notify(type="webhook", options={"url": h.url("/hook"), "headers": {"X-Key": "abc"}}))
        await n.send(alert())
        await n.close()
    (method, path, headers, body) = h.requests[0]
    assert method == "POST" and path == "/hook"
    assert json.loads(body) == alert()
    assert headers["Content-Type"].startswith("application/json")
    assert headers["X-Key"] == "abc"


async def test_webhook_raises_on_http_errors():
    async with Http(status=404) as h:
        n = WebhookNotifier(Notify(type="webhook", options={"url": h.url("/hook")}))
        with pytest.raises(Exception):
            await n.send(alert())
        await n.close()


# --- mqtt -----------------------------------------------------------------------------

def _varint(data, i):
    mult, value = 1, 0
    while True:
        b = data[i]
        i += 1
        value += (b & 0x7F) * mult
        mult *= 128
        if not b & 0x80:
            return value, i


def _str(data, i):
    n = int.from_bytes(data[i:i + 2], "big")
    return data[i + 2:i + 2 + n], i + 2 + n


class Broker:
    """A fake MQTT 3.1.1 broker that records CONNECT and PUBLISH packets."""

    def __init__(self, rc=0):
        self.rc = rc
        self.connects, self.publishes = [], []
        self.writers = []

    async def handle(self, reader, writer):
        self.writers.append(writer)
        try:
            while True:
                head = await reader.readexactly(1)
                length, mult = 0, 1
                while True:
                    b = (await reader.readexactly(1))[0]
                    length += (b & 0x7F) * mult
                    mult *= 128
                    if not b & 0x80:
                        break
                body = await reader.readexactly(length)
                kind = head[0] >> 4
                if kind == 1:   # CONNECT
                    proto, i = _str(body, 0)
                    level, flags = body[i], body[i + 1]
                    keepalive = int.from_bytes(body[i + 2:i + 4], "big")
                    i += 4
                    client, i = _str(body, i)
                    c = {"proto": proto, "level": level, "flags": flags, "keepalive": keepalive, "client": client}
                    if flags & 0x04:
                        c["will_topic"], i = _str(body, i)
                        c["will"], i = _str(body, i)
                    if flags & 0x80:
                        c["user"], i = _str(body, i)
                    if flags & 0x40:
                        c["password"], i = _str(body, i)
                    self.connects.append(c)
                    writer.write(bytes([0x20, 0x02, 0x00, self.rc]))
                    await writer.drain()
                elif kind == 3:  # PUBLISH (QoS 0)
                    topic, i = _str(body, 0)
                    self.publishes.append({"topic": topic.decode(), "payload": body[i:], "retain": bool(head[0] & 1)})
                elif kind == 12:  # PINGREQ
                    writer.write(bytes([0xD0, 0x00]))
                    await writer.drain()
                elif kind == 14:  # DISCONNECT
                    break
        except asyncio.IncompleteReadError:
            pass
        finally:
            writer.close()

    async def __aenter__(self):
        self.server = await asyncio.start_server(self.handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, *exc):
        for w in self.writers:
            w.close()
        self.server.close()

    def by_topic(self, topic):
        return [p for p in self.publishes if p["topic"] == topic]


async def settle(cond, tries=100):
    for _ in range(tries):
        if cond():
            return
        await asyncio.sleep(0.01)


async def test_mqtt_publishes_alerts_and_a_retained_armed_state():
    async with Broker() as b:
        n = MqttNotifier(Notify(type="mqtt", options={"host": "127.0.0.1", "port": b.port}))
        await n.send(alert())
        await n.armed(True)
        await n.armed(False)
        await settle(lambda: len(b.by_topic("porchlight/armed")) == 2)
        await n.close()
    (c,) = b.connects
    assert c["proto"] == b"MQTT" and c["level"] == 4
    assert c["will_topic"] == b"porchlight/status" and c["will"] == b"offline"
    (a,) = b.by_topic("porchlight/alert")
    assert json.loads(a["payload"]) == alert() and not a["retain"]
    assert [(p["payload"], p["retain"]) for p in b.by_topic("porchlight/armed")] == [(b"ON", True), (b"OFF", True)]
    assert b.by_topic("porchlight/status")[0]["payload"] == b"online"


async def test_mqtt_credentials_and_prefix():
    async with Broker() as b:
        n = MqttNotifier(Notify(type="mqtt", options={"host": "127.0.0.1", "port": b.port, "username": "u",
                                                      "password": "p", "topic_prefix": "house/porch"}))
        await n.send(alert())
        await settle(lambda: b.publishes)
        await n.close()
    assert b.connects[0]["user"] == b"u" and b.connects[0]["password"] == b"p"
    assert b.by_topic("house/porch/alert")


async def test_mqtt_home_assistant_discovery():
    async with Broker() as b:
        n = MqttNotifier(Notify(type="mqtt", options={"host": "127.0.0.1", "port": b.port, "discovery": True}))
        await n.armed(True)
        await settle(lambda: b.by_topic("porchlight/armed"))
        await n.close()
    configs = [p for p in b.publishes if p["topic"].startswith("homeassistant/") and p["topic"].endswith("/config")]
    assert configs and all(p["retain"] for p in configs)
    armed = json.loads(next(p for p in configs if "binary_sensor" in p["topic"])["payload"])
    assert armed["state_topic"] == "porchlight/armed" and armed["payload_on"] == "ON"
    assert armed["availability_topic"] == "porchlight/status"


async def test_mqtt_refused_connection_raises():
    async with Broker(rc=5) as b:
        n = MqttNotifier(Notify(type="mqtt", options={"host": "127.0.0.1", "port": b.port}))
        with pytest.raises(Exception):
            await n.send(alert())
        await n.close()


async def test_mqtt_reconnects_after_the_broker_drops_it():
    async with Broker() as b:
        n = MqttNotifier(Notify(type="mqtt", options={"host": "127.0.0.1", "port": b.port}))
        await n.send(alert())
        await settle(lambda: b.publishes)
        for w in b.writers:
            w.close()
        await asyncio.sleep(0.05)
        for _ in range(3):
            try:
                await n.send(alert())
                break
            except Exception:
                await asyncio.sleep(0.05)
        await settle(lambda: len(b.by_topic("porchlight/alert")) >= 2)
        await n.close()
    assert len(b.connects) == 2
    assert len(b.by_topic("porchlight/alert")) >= 2


def test_mqtt_needs_a_host():
    with pytest.raises(ValueError, match="host"):
        MqttNotifier(Notify(type="mqtt"))


def test_all_notifier_types_build():
    built = build_notifiers([Notify(type="ntfy", options={"url": "http://x/t"}),
                             Notify(type="webhook", options={"url": "http://x/h"}),
                             Notify(type="mqtt", options={"host": "x"})])
    assert [n.type for n, _ in built] == ["ntfy", "webhook", "mqtt"]
