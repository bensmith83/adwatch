"""Where tests find a parser binary and a fields table.

Both are supplied separately (README). Tests that need the binary skip
without it; the synthetic tests/fields.json stands in for the real table.
Point the scenario tests at the real pair with PORCHLIGHT_PARSER_BIN and
PORCHLIGHT_FIELDS.
"""

import os
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
BIN = Path(os.environ.get("PORCHLIGHT_PARSER_BIN", HERE.parent / "bin" / "macos" / "ble-parse"))
FIELDS = Path(os.environ.get("PORCHLIGHT_FIELDS", HERE / "fields.json"))

needs_bin = pytest.mark.skipif(not BIN.exists(), reason=f"no parser binary at {BIN}: set PORCHLIGHT_PARSER_BIN")
