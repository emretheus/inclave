"""Turn engine dataclasses into plain JSON-serializable dicts for the wire."""

from __future__ import annotations

from typing import Any

from inclave_core import FileEntry, InClaveConfig, Session


def file_entry(entry: FileEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "name": entry.name,
        "original_path": entry.original_path,
        "sha256": entry.sha256,
        "bytes": entry.bytes,
        "added_at": entry.added_at,
        "kind": entry.kind,
    }


def config(cfg: InClaveConfig) -> dict[str, Any]:
    return cfg.to_dict()


def session(sess: Session) -> dict[str, Any]:
    return sess.to_dict()


def model_info(info: Any, vram_ok: bool | None) -> dict[str, Any]:
    return {
        "name": info.name,
        "size_bytes": info.size_bytes,
        "family": info.family,
        "parameter_count": info.parameter_count,
        "is_default": info.is_default,
        "vram_ok": vram_ok,
    }
