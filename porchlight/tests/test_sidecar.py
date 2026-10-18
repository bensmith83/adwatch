import asyncio
import json
import os
import sys

import pytest

from porchlight.sidecar import ParseCache, Sidecar, run_contract

from parser_paths import BIN, needs_bin

# A stand-in for ble-parse: echoes the ad's name back as a parser name.
# "die" makes it exit (to exercise restarts); "slow" makes it sleep.
FAKE = r"""
import json, sys, time
for line in sys.stdin:
    ad = json.loads(line)
    if ad.get("name") == "die":
        sys.exit(1)
    if ad.get("name") == "slow":
        time.sleep(0.5)
    print(json.dumps({"results": [{"parser": ad.get("name") or "none", "beaconType": "x", "deviceClass": "x",
                                   "stableKey": None, "metadata": {}}]}), flush=True)
"""


def fake_cmd(tmp_path):
    p = tmp_path / "fake_parse.py"
    p.write_text(FAKE)
    return [sys.executable, str(p)]


def ad(name, addr="C0:FF:EE:00:00:01"):
    return {"t": 1, "addr": addr, "atype": "random", "rssi": -60, "mfr": None, "svc": {}, "uuids": [], "name": name, "tx": None}


async def test_answers_come_back_in_order(tmp_path):
    sc = Sidecar(fake_cmd(tmp_path))
    await sc.start()
    try:
        outs = await asyncio.gather(*(sc.parse(ad(f"p{i}")) for i in range(50)))
        assert [o[0]["parser"] for o in outs] == [f"p{i}" for i in range(50)]
    finally:
        await sc.stop()


async def test_a_dead_child_is_restarted_and_its_ads_are_dropped(tmp_path, caplog):
    sc = Sidecar(fake_cmd(tmp_path), backoff_initial=0.05)
    await sc.start()
    try:
        assert (await sc.parse(ad("a")))[0]["parser"] == "a"
        assert await sc.parse(ad("die")) is None
        assert sc.dropped >= 1
        for _ in range(100):
            out = await sc.parse(ad("b"))
            if out is not None:
                break
            await asyncio.sleep(0.02)
        assert out[0]["parser"] == "b"
        assert sc.restarts >= 1
        assert "dropped" in caplog.text or "restart" in caplog.text
    finally:
        await sc.stop()


async def test_ads_during_the_gap_are_dropped_not_queued(tmp_path):
    sc = Sidecar(fake_cmd(tmp_path), backoff_initial=0.5)
    await sc.start()
    try:
        await sc.parse(ad("die"))
        assert await sc.parse(ad("c")) is None
    finally:
        await sc.stop()


async def test_a_missing_binary_does_not_crash_the_caller(tmp_path):
    sc = Sidecar([str(tmp_path / "nope")], backoff_initial=0.05)
    await sc.start()
    try:
        assert await sc.parse(ad("a")) is None
    finally:
        await sc.stop()


def test_parse_cache_keys_on_content_not_rssi_or_time():
    c = ParseCache(maxsize=2)
    a = ad("x")
    c.put(a, [{"parser": "x"}])
    assert c.get(dict(a, rssi=-90, t=999, tx=4)) == [{"parser": "x"}]
    assert c.get(dict(a, name="y")) is None
    assert c.get(dict(a, addr="C0:FF:EE:00:00:02")) is None


def test_parse_cache_is_bounded():
    c = ParseCache(maxsize=2)
    for n in "abc":
        c.put(ad(n), [])
    assert c.get(ad("a")) is None
    assert c.get(ad("c")) == []
    assert len(c) == 2


@needs_bin
async def test_contract_against_the_real_binary():
    failures = await run_contract([str(BIN)])
    assert failures == []
