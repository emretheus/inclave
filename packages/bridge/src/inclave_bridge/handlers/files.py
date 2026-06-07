"""files.* handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from inclave_core import add_file, clear_workspace, list_files, remove_file

from inclave_bridge import serialize


def add(params: dict[str, Any]) -> list[dict[str, Any]]:
    paths = [Path(p).expanduser() for p in params.get("paths", [])]
    out: list[dict[str, Any]] = []
    for p in paths:
        entry, _was_new = add_file(p)
        out.append(serialize.file_entry(entry))
    return out


def list_(params: dict[str, Any]) -> list[dict[str, Any]]:
    return [serialize.file_entry(f) for f in list_files()]


def remove(params: dict[str, Any]) -> dict[str, Any]:
    entry = remove_file(str(params["ref"]))
    return serialize.file_entry(entry)


def clear(params: dict[str, Any]) -> dict[str, Any]:
    n = clear_workspace()
    return {"removed": n}
