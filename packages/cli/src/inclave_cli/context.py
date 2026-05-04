"""Prompt context: pick workspace files and build the system+user prompt."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from inclave_core.workspace import FileEntry, find_file, list_files

from inclave_cli.files import (
    MAX_FILES,
    MAX_PER_FILE_BYTES,
    MAX_TOTAL_BYTES,
    parse,
)

SYSTEM_PROMPT = """\
You are InClave, a privacy-first local file analysis assistant.
All data stays on the user's machine; you may never invent file contents.

Rules:
- Ground every answer in the attached file blocks below. If the data isn't
  there, say so plainly — don't guess.
- When asked to compute, summarize, or extract, prefer writing a Python
  script the user can run via /run. The sandbox provides:
    pandas, numpy, openpyxl, pypdf, matplotlib (Agg) + the Python stdlib.
  No network is available. The script's working directory contains copies
  of the attached files (same names as shown in the file blocks).
- Be terse. Show numbers, tables, or a short code block — not paragraphs.
"""


@dataclass(frozen=True)
class AttachedFile:
    entry: FileEntry
    text: str
    truncated_bytes: int


def select_files(refs: list[str] | None) -> list[FileEntry]:
    """If refs given, resolve them; otherwise return everything in workspace."""
    if refs:
        return [find_file(r) for r in refs]
    return list_files()


def attach(entries: list[FileEntry]) -> tuple[list[AttachedFile], list[str]]:
    """Parse + apply per-file and total caps.

    Returns (attached, warnings).
    """
    warnings: list[str] = []
    if len(entries) > MAX_FILES:
        warnings.append(
            f"{len(entries)} files selected; using first {MAX_FILES} (limit per session)"
        )
        entries = entries[:MAX_FILES]

    attached: list[AttachedFile] = []
    total = 0
    for e in entries:
        path = e.stored_path()
        try:
            text = parse(path)
        except Exception as exc:
            warnings.append(f"skipping {e.name}: {exc}")
            continue
        raw = text.encode("utf-8")
        truncated = 0
        if len(raw) > MAX_PER_FILE_BYTES:
            truncated = len(raw) - MAX_PER_FILE_BYTES
            text = raw[:MAX_PER_FILE_BYTES].decode("utf-8", errors="replace")
            text += f"\n\n[... truncated, {truncated // 1024} KB omitted ...]"
        # Total budget
        encoded = text.encode("utf-8")
        if total + len(encoded) > MAX_TOTAL_BYTES:
            remaining = MAX_TOTAL_BYTES - total
            if remaining <= 0:
                warnings.append(f"skipping {e.name}: total context budget reached")
                continue
            text = encoded[:remaining].decode("utf-8", errors="replace")
            text += "\n\n[... truncated, total context budget reached ...]"
            truncated += len(encoded) - remaining
        attached.append(AttachedFile(entry=e, text=text, truncated_bytes=truncated))
        total += len(text.encode("utf-8"))

    return attached, warnings


def render_file_block(af: AttachedFile) -> str:
    header = f"<<<FILE id={af.entry.id} name={af.entry.name} kind={af.entry.kind}>>>"
    return f"{header}\n{af.text}\n<<<END FILE>>>"


def assemble_user_prompt(question: str, attached: list[AttachedFile]) -> str:
    if not attached:
        return question
    blocks = "\n\n".join(render_file_block(a) for a in attached)
    return f"{blocks}\n\n---\n\n{question}"


def write_run_workdir(target: Path, attached: list[AttachedFile]) -> None:
    """Copy the workspace files (originals from the workspace store, not the
    truncated text) into a temp dir that becomes the sandbox workdir.
    """
    target.mkdir(parents=True, exist_ok=True)
    for af in attached:
        src = af.entry.stored_path()
        if src.is_file():
            (target / af.entry.name).write_bytes(src.read_bytes())
