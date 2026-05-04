"""Smoke tests for the UI helpers."""

from __future__ import annotations

import io
from datetime import UTC

from enclave_cli import ui
from rich.console import Console


def _console() -> tuple[Console, io.StringIO]:
    buf = io.StringIO()
    return Console(file=buf, width=120, force_terminal=False, highlight=False), buf


def test_banner_shows_state() -> None:
    c, buf = _console()
    ui.banner(c, "llama3.2:latest", 2, "/tmp/x")
    out = buf.getvalue()
    assert "enclave" in out
    assert "llama3.2:latest" in out
    assert "2 files" in out
    assert "/tmp/x" in out


def test_status_hint_singular_plural() -> None:
    c, buf = _console()
    ui.status_hint(c, model="m1", n_files=1, n_turns=1, workdir="/tmp/x")
    out = buf.getvalue()
    assert "1 file" in out and "1 turn" in out
    assert "/tmp/x" in out

    c, buf = _console()
    ui.status_hint(c, model="m1", n_files=0, n_turns=3, workdir="/tmp/x")
    out = buf.getvalue()
    assert "0 files" in out and "3 turns" in out


def test_render_markdown_renders_headers() -> None:
    c, buf = _console()
    ui.render_markdown(c, "# Title\n\n- item one\n- item two\n")
    out = buf.getvalue()
    assert "Title" in out
    assert "item one" in out


def test_render_markdown_handles_code_fence() -> None:
    c, buf = _console()
    ui.render_markdown(c, "```python\nprint('hi')\n```\n")
    out = buf.getvalue()
    assert "print" in out


def test_render_sandbox_output_uses_seconds_for_long_runs() -> None:
    c, buf = _console()
    ui.render_sandbox_output(
        c, stdout="ok", stderr="", exit_code=0, duration_ms=2300, timed_out=False
    )
    out = buf.getvalue()
    assert "2.3s" in out


def test_render_sandbox_output_shows_ms_for_short_runs() -> None:
    c, buf = _console()
    ui.render_sandbox_output(
        c, stdout="ok", stderr="", exit_code=0, duration_ms=42, timed_out=False
    )
    out = buf.getvalue()
    assert "42 ms" in out


def test_render_files_marks_attached() -> None:
    from datetime import datetime

    from enclave_core.workspace import FileEntry

    e1 = FileEntry(
        id="aaa11111",
        name="x.csv",
        original_path="/tmp/x.csv",
        sha256="aaa",
        bytes=10,
        added_at=datetime.now(UTC).isoformat(),
        kind="csv",
    )
    e2 = FileEntry(
        id="bbb22222",
        name="y.txt",
        original_path="/tmp/y.txt",
        sha256="bbb",
        bytes=20,
        added_at=datetime.now(UTC).isoformat(),
        kind="text",
    )

    c, buf = _console()
    ui.render_files(c, [e1, e2], attached_ids={e1.id})
    out = buf.getvalue()
    assert "x.csv" in out and "y.txt" in out
