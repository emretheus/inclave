"""config.* handlers."""

from __future__ import annotations

from typing import Any

from inclave_core import load_config, set_config_value

from inclave_bridge import serialize


def get(params: dict[str, Any]) -> dict[str, Any]:
    return serialize.config(load_config())


def set_(params: dict[str, Any]) -> dict[str, Any]:
    key = str(params["key"])
    value = str(params["value"])
    cfg = set_config_value(key, value)
    return serialize.config(cfg)
