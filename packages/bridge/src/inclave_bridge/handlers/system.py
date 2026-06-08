"""system.* and ollama.* handlers."""

from __future__ import annotations

import shutil
from typing import Any

from inclave_cli.onboarding import _ollama_up, _spawn_ollama_daemon
from inclave_ollama.hardware import get_total_ram_gb


def _sandbox_ok() -> bool:
    return shutil.which("sandbox-exec") is not None


def _default_model() -> str | None:
    try:
        from inclave_ollama.api import get_default as _gd

        return _gd()
    except Exception:
        return None


def status(params: dict[str, Any]) -> dict[str, Any]:
    ram = get_total_ram_gb()
    return {
        "ollama_running": _ollama_up(),
        "default_model": _default_model(),
        "ram_gb": round(ram, 1) if ram else None,
        "sandbox_ok": _sandbox_ok(),
    }


def ensure_running(params: dict[str, Any]) -> dict[str, Any]:
    if _ollama_up():
        return {"running": True, "already": True}
    if shutil.which("ollama") is None:
        return {
            "running": False,
            "installed": False,
            "hint": "Install Ollama: brew install ollama",
        }
    try:
        _spawn_ollama_daemon()
    except Exception as exc:  # pragma: no cover — defensive
        return {"running": False, "error": str(exc)}
    # Poll briefly for it to come up.
    import time

    for _ in range(20):
        if _ollama_up(timeout=0.5):
            return {"running": True, "already": False}
        time.sleep(0.5)
    return {"running": False, "error": "ollama did not come up in time"}


__all__ = ["ensure_running", "status"]
