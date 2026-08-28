"""CLI configuration — stored in ~/.modelbridge/config.json."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(os.environ.get("MODELBRIDGE_CONFIG_DIR", Path.home() / ".modelbridge"))
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "url": "http://localhost:8000",
    "api_key": None,
    "access_token": None,
    "org_id": None,
    "email": None,
}


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return dict(DEFAULTS)
    with CONFIG_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    merged = dict(DEFAULTS)
    merged.update(data)
    return merged


def save_config(data: dict[str, Any]) -> None:
    _ensure_dir()
    current = load_config()
    current.update(data)
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    try:
        CONFIG_FILE.chmod(0o600)
    except OSError:
        pass


def get(key: str) -> Any:
    return load_config().get(key)


def set_value(key: str, value: Any) -> None:
    save_config({key: value})


def clear_config() -> None:
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()


def mask_secret(value: str | None) -> str:
    if not value:
        return "(not set)"
    if len(value) <= 8:
        return "****"
    return value[:4] + "..." + value[-4:]


def show_config() -> dict[str, str]:
    cfg = load_config()
    return {
        "url": cfg.get("url") or DEFAULTS["url"],
        "api_key": mask_secret(cfg.get("api_key")),
        "access_token": mask_secret(cfg.get("access_token")),
        "org_id": cfg.get("org_id") or "(not set)",
        "email": cfg.get("email") or "(not set)",
    }
