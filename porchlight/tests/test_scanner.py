import json
from types import SimpleNamespace

from porchlight.capture import CaptureWriter
from porchlight.scanner import Throttle, to_ad


def device(addr="C0:FF:EE:00:00:01", props=None):
    return SimpleNamespace(address=addr, details={"props": props or {}})


def adv(**kw):
    d = dict(manufacturer_data={}, service_data={}, service_uuids=[], local_name=None, rssi=-67, tx_power=None)
    d.update(kw)
    return SimpleNamespace(**d)


def test_to_ad_matches_the_sidecar_input():
    a = to_ad(device(props={"AddressType": "random"}),
              adv(manufacturer_data={0x004C: bytes.fromhex("0215")},
                  service_data={"0000fe07-0000-1000-8000-00805f9b34fb": b"\x01\xab"},
                  service_uuids=["0000fe07-0000-1000-8000-00805f9b34fb"], local_name="S39 ABCD LE", tx_power=4),
              now_ms=1760000000123)
    assert a == {"t": 1760000000123, "addr": "C0:FF:EE:00:00:01", "atype": "random", "rssi": -67,
                 "mfr": "4c000215", "svc": {"0000fe07-0000-1000-8000-00805f9b34fb": "01ab"},
                 "uuids": ["0000fe07-0000-1000-8000-00805f9b34fb"], "name": "S39 ABCD LE", "tx": 4}
    json.dumps(a)


def test_address_type_comes_from_bluez_props():
    assert to_ad(device(props={"AddressType": "public"}), adv(), 0)["atype"] == "public"
    assert to_ad(device(props={}), adv(), 0)["atype"] == "random"
    assert to_ad(SimpleNamespace(address="C0:FF:EE:00:00:01", details=None), adv(), 0)["atype"] == "random"


def test_empty_fields_are_null():
    a = to_ad(device(), adv(), 0)
    assert a["mfr"] is None and a["svc"] == {} and a["uuids"] == [] and a["name"] is None


def test_throttle_passes_one_sighting_per_second_per_payload():
    th = Throttle(interval=1.0)
    a = {"addr": "C0:FF:EE:00:00:01", "atype": "random", "mfr": "aa", "svc": {}, "uuids": [], "name": None}
    assert th.allow(a, 0.0)
    assert not th.allow(dict(a, rssi=-50), 0.5)
    assert th.allow(dict(a, mfr="bb"), 0.5), "a different frame from the same radio is its own stream"
    assert th.allow(a, 1.0)


def test_throttle_forgets_old_entries():
    th = Throttle(interval=1.0)
    for i in range(100):
        th.allow({"addr": f"40:00:00:00:00:{i:02X}"}, float(i))
    th.prune(1000.0)
    assert len(th) == 0


def test_capture_writes_jsonl_and_rotates_daily(tmp_path):
    days = iter(["2026-10-17", "2026-10-17", "2026-10-18"])
    w = CaptureWriter(str(tmp_path / "capture.jsonl"), max_mb=1, today=lambda: next(days))
    for i in range(3):
        w.write({"t": i, "addr": "C0:FF:EE:00:00:01"})
    w.close()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["capture-2026-10-17.jsonl", "capture-2026-10-18.jsonl"]
    lines = (tmp_path / "capture-2026-10-17.jsonl").read_text().splitlines()
    assert [json.loads(l)["t"] for l in lines] == [0, 1]


def test_capture_stops_at_its_size_cap(tmp_path):
    w = CaptureWriter(str(tmp_path / "capture.jsonl"), max_mb=0.001, today=lambda: "2026-10-17")
    for i in range(1000):
        w.write({"t": i, "addr": "C0:FF:EE:00:00:01", "pad": "x" * 50})
    w.close()
    size = (tmp_path / "capture-2026-10-17.jsonl").stat().st_size
    assert size <= 1100


def test_capture_keeps_a_week(tmp_path):
    for d in range(1, 12):
        (tmp_path / f"capture-2026-10-{d:02d}.jsonl").write_text("{}\n")
    w = CaptureWriter(str(tmp_path / "capture.jsonl"), max_mb=1, today=lambda: "2026-10-12", keep_days=7)
    w.write({"t": 1})
    w.close()
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names[0] == "capture-2026-10-06.jsonl" and names[-1] == "capture-2026-10-12.jsonl"
    assert len(names) == 7


class FakeBleak:
    """Records how the scanner builds bleak's BleakScanner."""
    made = []

    def __init__(self, detection_callback=None, **kwargs):
        self.callback = detection_callback
        self.kwargs = kwargs
        FakeBleak.made.append(self)

    async def start(self):
        pass

    async def stop(self):
        pass


async def test_scanner_asks_bluez_for_active_scanning_without_duplicate_filtering():
    from porchlight.scanner import Scanner

    got = []
    FakeBleak.made.clear()
    s = Scanner("hci1", got.append, scanner_cls=FakeBleak)
    await s.start()
    (b,) = FakeBleak.made
    assert b.kwargs["scanning_mode"] == "active"
    assert b.kwargs["bluez"] == {"adapter": "hci1", "filters": {"DuplicateData": True}}
    assert "adapter" not in b.kwargs, "bleak 3 deprecates the adapter keyword"
    b.callback(device(), adv(local_name="x"))
    b.callback(device(), adv(local_name="x"))       # same payload within a second: throttled
    assert len(got) == 1 and got[0]["name"] == "x"
    await s.stop()


async def test_a_scanner_start_failure_says_what_to_check():
    import pytest
    from porchlight.scanner import Scanner

    class NoBus(FakeBleak):
        async def start(self):
            raise FileNotFoundError(2, "No such file or directory")

    s = Scanner("hci1", lambda ad: None, scanner_cls=NoBus)
    with pytest.raises(RuntimeError) as e:
        await s.start()
    msg = str(e.value)
    assert "hci1" in msg and "bluetoothd" in msg and "No such file" in msg
