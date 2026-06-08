"""models.* handlers."""

from __future__ import annotations

import re
from typing import Any

from inclave_ollama.api import (
    is_model_fully_vram_compatible,
    list_models,
    pull_model,
    remove_model,
    set_default,
)

from inclave_bridge import serialize
from inclave_bridge.events import EventEmitter

# pull_model yields strings like "downloading (12345/67890)" — pull the numbers
# back out so the UI can render a real progress bar.
_PROGRESS_RE = re.compile(r"^(?P<status>.*?)\s*\((?P<done>\d+)/(?P<total>\d+)\)\s*$")


def list_(params: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for info in list_models():
        vram_ok = is_model_fully_vram_compatible(info.size_bytes)
        out.append(serialize.model_info(info, vram_ok))
    return out


def remove(params: dict[str, Any]) -> dict[str, Any]:
    remove_model(str(params["name"]))
    return {"removed": True}


def set_default_(params: dict[str, Any]) -> dict[str, Any]:
    name = str(params["name"])
    set_default(name)
    return {"default_model": name}


def pull(params: dict[str, Any], emitter: EventEmitter) -> dict[str, Any]:
    name = str(params["name"])
    for line in pull_model(name):
        m = _PROGRESS_RE.match(line)
        if m:
            emitter.models_pull_progress(
                name,
                m.group("status").strip(),
                int(m.group("done")),
                int(m.group("total")),
            )
        else:
            emitter.models_pull_progress(name, line.strip(), 0, 0)
    return {"pulled": True, "name": name}
