import asyncio
import logging

import pytest

from porchlight.config import Notify
from porchlight.notify import Dispatcher, build_notifiers
from porchlight.notify.base import Notifier
from porchlight.notify.log import LogNotifier


def alert(severity="alert", id=1, rule="R1"):
    return {"id": id, "rule": rule, "severity": severity, "created": 1760000000.0, "title": "Lingering stranger",
            "message": "Watch (Acme; Serial; …0001) has been near for 12 min", "unit": {"hint": "0001"}}


class Recorder(Notifier):
    type = "recorder"

    def __init__(self, fail=0, hang=False):
        self.sent, self.states, self.fail, self.hang, self.calls = [], [], fail, hang, 0

    async def send(self, a):
        self.calls += 1
        if self.hang:
            await asyncio.sleep(3600)
        if self.calls <= self.fail:
            raise RuntimeError("boom")
        self.sent.append(a)

    async def armed(self, armed):
        self.states.append(armed)


async def drain(d):
    for _ in range(50):
        await asyncio.sleep(0.01)
        if d.idle():
            return


async def test_alerts_go_to_notifiers_at_or_above_their_min_severity():
    loud, quiet = Recorder(), Recorder()
    d = Dispatcher([(loud, "warn"), (quiet, "alert")], backoff=0)
    d.start()
    d.submit(alert("warn", id=1))
    d.submit(alert("alert", id=2))
    await drain(d)
    await d.stop()
    assert [a["id"] for a in loud.sent] == [1, 2]
    assert [a["id"] for a in quiet.sent] == [2]


async def test_info_is_never_pushed():
    r = Recorder()
    d = Dispatcher([(r, "info")], backoff=0)
    d.start()
    d.submit(alert("info"))
    await drain(d)
    await d.stop()
    assert r.sent == []


async def test_a_failing_notifier_is_retried_then_the_alert_is_dropped_and_logged(caplog):
    flaky, broken = Recorder(fail=2), Recorder(fail=99)
    d = Dispatcher([(flaky, "warn"), (broken, "warn")], retries=3, backoff=0)
    d.start()
    with caplog.at_level(logging.WARNING):
        d.submit(alert())
        await drain(d)
    await d.stop()
    assert len(flaky.sent) == 1 and flaky.calls == 3
    assert broken.sent == [] and broken.calls == 4
    assert "dropped" in caplog.text


async def test_a_hung_notifier_blocks_neither_the_caller_nor_the_others():
    hung, ok = Recorder(hang=True), Recorder()
    d = Dispatcher([(hung, "warn"), (ok, "warn")], backoff=0, timeout=0.05, retries=0)
    d.start()
    for i in range(5):
        d.submit(alert(id=i))
    await drain(d)
    await d.stop()
    assert [a["id"] for a in ok.sent] == [0, 1, 2, 3, 4]


async def test_submit_never_blocks_when_the_queue_is_full(caplog):
    d = Dispatcher([(Recorder(), "warn")], queue_max=2)
    for i in range(10):          # not started: nothing drains
        d.submit(alert(id=i))
    assert d.dropped == 8


async def test_armed_state_reaches_notifiers_that_want_it():
    r = Recorder()
    d = Dispatcher([(r, "warn")], backoff=0)
    d.start()
    d.submit_armed(True)
    await drain(d)
    await d.stop()
    assert r.states == [True]


async def test_log_notifier_writes_one_line(caplog):
    with caplog.at_level(logging.INFO, logger="porchlight.alerts"):
        await LogNotifier(Notify(type="log")).send(alert())
    assert "R1" in caplog.text and "Lingering stranger" in caplog.text and "…0001" in caplog.text


def test_build_notifiers_from_config():
    built = build_notifiers([Notify(type="log", min_severity="alert"), Notify(type="page")])
    assert [(n.type, s) for n, s in built] == [("log", "alert")]


def test_unknown_notifier_type_is_an_error():
    with pytest.raises(ValueError, match="carrier pigeon"):
        build_notifiers([Notify(type="carrier pigeon")])
