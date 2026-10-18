#!/usr/bin/env python3
"""Measure ble-parse throughput and peak RSS (SPEC §4.1 budget, M0).

  python3 scripts/bench_parser.py /opt/porchlight/bin/ble-parse [--n 20000]

Feeds the synthetic contract ads (fake addresses, every one distinct) through
the binary as one stream and reports ads/s and peak RSS against the budget:
at least 200 ads/s at under 60 MB RSS on a Pi Zero 2 W. Standard library
only, so it runs on the Pi as-is.
"""

import argparse
import json
import resource
import subprocess
import sys
import threading
import time
from pathlib import Path

BUDGET_ADS_S = 200
BUDGET_RSS_MB = 60
CONTRACT = Path(__file__).resolve().parent.parent / "porchlight" / "sidecar_contract.json"


def ads(n: int, contract: Path):
    cases = [c["ad"] for c in json.loads(contract.read_text())["cases"]]
    for i in range(n):
        ad = dict(cases[i % len(cases)])
        ad["addr"] = "5C:FF:%02X:%02X:%02X:%02X" % (i >> 24 & 255, i >> 16 & 255, i >> 8 & 255, i & 255)
        ad["t"] = 1_760_000_000_000 + i
        yield json.dumps(ad) + "\n"


def peak_rss_mb() -> float:
    kb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return kb / 1024 / (1024 if sys.platform == "darwin" else 1)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("binary")
    p.add_argument("--n", type=int, default=20000)
    p.add_argument("--contract", type=Path, default=CONTRACT)
    args = p.parse_args()

    payload = "".join(ads(args.n, args.contract)).encode()
    proc = subprocess.Popen([args.binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    lines = 0

    def read():
        nonlocal lines
        for _ in proc.stdout:
            lines += 1

    reader = threading.Thread(target=read)
    reader.start()
    start = time.monotonic()
    proc.stdin.write(payload)
    proc.stdin.close()
    reader.join()
    proc.wait()
    elapsed = time.monotonic() - start
    rate = lines / elapsed if elapsed else 0
    rss = peak_rss_mb()
    ok = lines == args.n and rate >= BUDGET_ADS_S and rss < BUDGET_RSS_MB
    print(f"{lines}/{args.n} answers in {elapsed:.2f} s: {rate:,.0f} ads/s (budget {BUDGET_ADS_S}), "
          f"peak RSS {rss:.1f} MB (budget < {BUDGET_RSS_MB})  {'OK' if ok else 'OVER BUDGET'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
