"""Configuration via environment variables with sensible defaults."""

import os


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    return int(os.environ.get(key, str(default)))


ADAPTER = _env("ADWATCH_ADAPTER", "hci0")
DB_PATH = _env("ADWATCH_DB_PATH", "./adwatch.db")
HOST = _env("ADWATCH_HOST", "0.0.0.0")
PORT = _env_int("ADWATCH_PORT", 8080)
RAW_RETENTION_DAYS = _env_int("ADWATCH_RAW_RETENTION_DAYS", 7)
PARSED_RETENTION_DAYS = _env_int("ADWATCH_PARSED_RETENTION_DAYS", 30)
LOG_LEVEL = _env("ADWATCH_LOG_LEVEL", "INFO")
DISABLED_PLUGINS = [p.strip() for p in _env("ADWATCH_DISABLED_PLUGINS", "").split(",") if p.strip()]
