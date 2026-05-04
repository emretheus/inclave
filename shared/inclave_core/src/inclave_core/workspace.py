"""Local-only file workspace.

Files are *copied* into ~/.inclave/workspaces/<name>/files/ keyed by content hash,
so the original is never depended on. A manifest (manifest.json) records original
path, size, hash, and add time.

Demo: only one workspace named "default". Multi-workspace lands later.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from inclave_core.config import enclave_dir
from inclave_core.errors import CLIError, ConfigError

_DEFAULT = "default"


def workspaces_root() -> Path:
    d = enclave_dir() / "workspaces"
    d.mkdir(parents=True, exist_ok=True)
    return d


def workspace_dir(name: str = _DEFAULT) -> Path:
    d = workspaces_root() / name
    (d / "files").mkdir(parents=True, exist_ok=True)
    return d


def _manifest_path(name: str = _DEFAULT) -> Path:
    return workspace_dir(name) / "manifest.json"


@dataclass
class FileEntry:
    id: str
    name: str
    original_path: str
    sha256: str
    bytes: int
    added_at: str
    kind: str  # "text" | "csv" | "xlsx" | "pdf" | "code" | "other"

    def stored_path(self, name: str = _DEFAULT) -> Path:
        return workspace_dir(name) / "files" / f"{self.id}__{self.name}"


@dataclass
class Manifest:
    version: int = 1
    files: list[FileEntry] = field(default_factory=list)


def load_manifest(name: str = _DEFAULT) -> Manifest:
    path = _manifest_path(name)
    if not path.exists():
        return Manifest()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise ConfigError(f"workspace manifest unreadable: {e}") from e
    files = [FileEntry(**f) for f in data.get("files", [])]
    return Manifest(version=data.get("version", 1), files=files)


def save_manifest(manifest: Manifest, name: str = _DEFAULT) -> None:
    path = _manifest_path(name)
    tmp = path.with_suffix(".json.tmp")
    payload = {
        "version": manifest.version,
        "files": [asdict(f) for f in manifest.files],
    }
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


_KIND_BY_EXT: dict[str, str] = {
    ".txt": "text",
    ".md": "text",
    ".csv": "csv",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".pdf": "pdf",
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".tsx": "code",
    ".jsx": "code",
    ".go": "code",
    ".rs": "code",
    ".java": "code",
    ".c": "code",
    ".cpp": "code",
    ".h": "code",
    ".hpp": "code",
    ".rb": "code",
    ".sh": "code",
    ".sql": "code",
    ".json": "code",
    ".yaml": "code",
    ".yml": "code",
    ".toml": "code",
    ".html": "code",
    ".css": "code",
}


def kind_for(path: Path) -> str:
    return _KIND_BY_EXT.get(path.suffix.lower(), "other")


def _hash_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    with path.open("rb") as f:
        while chunk := f.read(64 * 1024):
            h.update(chunk)
            n += len(chunk)
    return h.hexdigest(), n


def add_file(src: Path, name: str = _DEFAULT) -> tuple[FileEntry, bool]:
    """Copy `src` into the workspace. Returns (entry, was_new)."""
    src = src.expanduser().resolve()
    if not src.is_file():
        raise CLIError(f"not a file: {src}")

    digest, size = _hash_file(src)
    file_id = digest[:8]
    manifest = load_manifest(name)

    for existing in manifest.files:
        if existing.sha256 == digest:
            return existing, False

    entry = FileEntry(
        id=file_id,
        name=src.name,
        original_path=str(src),
        sha256=digest,
        bytes=size,
        added_at=datetime.now(UTC).isoformat(timespec="seconds"),
        kind=kind_for(src),
    )
    dest = entry.stored_path(name)
    shutil.copy2(src, dest)
    manifest.files.append(entry)
    save_manifest(manifest, name)
    return entry, True


def remove_file(ref: str, name: str = _DEFAULT) -> FileEntry:
    """Remove by id (8-char prefix) or by file name. Returns the removed entry."""
    manifest = load_manifest(name)
    matches = [
        f for f in manifest.files if f.id == ref or f.name == ref or f.sha256.startswith(ref)
    ]
    if not matches:
        raise CLIError(f"no file in workspace matches: {ref}")
    if len(matches) > 1:
        names = ", ".join(f"{m.id} ({m.name})" for m in matches)
        raise CLIError(f"ambiguous reference {ref!r}, matches: {names}")
    entry = matches[0]
    stored = entry.stored_path(name)
    if stored.exists():
        stored.unlink()
    manifest.files = [f for f in manifest.files if f.sha256 != entry.sha256]
    save_manifest(manifest, name)
    return entry


def find_file(ref: str, name: str = _DEFAULT) -> FileEntry:
    manifest = load_manifest(name)
    matches = [
        f for f in manifest.files if f.id == ref or f.name == ref or f.sha256.startswith(ref)
    ]
    if not matches:
        raise CLIError(f"no file in workspace matches: {ref}")
    if len(matches) > 1:
        names = ", ".join(f"{m.id} ({m.name})" for m in matches)
        raise CLIError(f"ambiguous reference {ref!r}, matches: {names}")
    return matches[0]


def clear_workspace(name: str = _DEFAULT) -> int:
    """Remove all files. Returns count removed."""
    manifest = load_manifest(name)
    n = len(manifest.files)
    files_dir = workspace_dir(name) / "files"
    for entry in manifest.files:
        p = entry.stored_path(name)
        if p.exists():
            p.unlink()
    # Also clear any orphans
    if files_dir.exists():
        for p in files_dir.iterdir():
            if p.is_file():
                p.unlink()
    save_manifest(Manifest(), name)
    return n


def list_files(name: str = _DEFAULT) -> list[FileEntry]:
    return load_manifest(name).files
