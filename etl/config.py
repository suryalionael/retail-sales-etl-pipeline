from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "pipeline.yml"


def _expand(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {key: _expand(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand(item) for item in value]
    return value


def load_config(config_path: Path | str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env")
    with Path(config_path).open("r", encoding="utf-8") as handle:
        raw_config = yaml.safe_load(handle)
    return _expand(raw_config)


def database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://retail:retail@localhost:5432/retail_warehouse",
    )
