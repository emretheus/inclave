"""Tests for the parser dispatcher and `inclave files` commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from inclave_cli.files import parse
from inclave_cli.main import app
from inclave_core.errors import CLIError
from typer.testing import CliRunner

runner = CliRunner()


def test_parse_text(tmp_path: Path) -> None:
    p = tmp_path / "notes.md"
    p.write_text("# Hello\n\nworld")
    out = parse(p)
    assert "Hello" in out


def test_parse_csv(tmp_path: Path) -> None:
    p = tmp_path / "data.csv"
    p.write_text("name,age\nalice,30\nbob,25\n")
    out = parse(p)
    assert "name" in out and "alice" in out
    assert "|" in out  # markdown table


def test_parse_code_fences_python(tmp_path: Path) -> None:
    p = tmp_path / "x.py"
    p.write_text("def f():\n    return 1\n")
    out = parse(p)
    assert out.startswith("```py")
    assert "def f" in out


def test_parse_unsupported(tmp_path: Path) -> None:
    p = tmp_path / "blob.bin"
    p.write_bytes(b"\x00\x01")
    with pytest.raises(CLIError):
        parse(p)


def test_parse_xlsx(tmp_path: Path) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["name", "age"])
    ws.append(["alice", 30])
    ws.append(["bob", 25])
    p = tmp_path / "x.xlsx"
    wb.save(p)
    out = parse(p)
    assert "Sheet: Sheet1" in out
    assert "alice" in out


def test_parse_pdf(tmp_path: Path) -> None:
    pypdf = pytest.importorskip("pypdf")
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    p = tmp_path / "x.pdf"
    with p.open("wb") as f:
        writer.write(f)
    out = parse(p)
    assert "PDF: x.pdf" in out
    assert "1 pages" in out
    assert pypdf  # silence unused


def test_files_add_list_remove(fake_home: Path, tmp_path: Path) -> None:
    src = tmp_path / "doc.txt"
    src.write_text("hello")

    r1 = runner.invoke(app, ["files", "add", str(src)])
    assert r1.exit_code == 0, r1.output
    assert "added" in r1.output

    r2 = runner.invoke(app, ["files", "list"])
    assert r2.exit_code == 0
    assert "doc.txt" in r2.output

    r3 = runner.invoke(app, ["files", "remove", "doc.txt"])
    assert r3.exit_code == 0
    assert "removed" in r3.output

    r4 = runner.invoke(app, ["files", "list"])
    assert "workspace is empty" in r4.output


def test_files_add_dedup(fake_home: Path, tmp_path: Path) -> None:
    src = tmp_path / "doc.txt"
    src.write_text("same")
    runner.invoke(app, ["files", "add", str(src)])
    r2 = runner.invoke(app, ["files", "add", str(src)])
    assert r2.exit_code == 0
    assert "already" in r2.output


def test_files_clear_with_yes(fake_home: Path, tmp_path: Path) -> None:
    src = tmp_path / "x.txt"
    src.write_text("x")
    runner.invoke(app, ["files", "add", str(src)])
    r = runner.invoke(app, ["files", "clear", "--yes"])
    assert r.exit_code == 0
    assert "removed 1" in r.output


def test_files_show(fake_home: Path, tmp_path: Path) -> None:
    src = tmp_path / "n.md"
    src.write_text("# Title")
    runner.invoke(app, ["files", "add", str(src)])
    r = runner.invoke(app, ["files", "show", "n.md"])
    assert r.exit_code == 0
    assert "Title" in r.output


def test_ask_attaches_workspace(fake_home: Path, tmp_path: Path) -> None:
    """`inclave ask` auto-attaches workspace files and includes them in the prompt."""
    from unittest.mock import patch

    src = tmp_path / "secret.txt"
    src.write_text("the secret is 42")
    runner.invoke(app, ["models", "use", "m1"])
    runner.invoke(app, ["files", "add", str(src)])

    captured: dict[str, object] = {}

    def fake_generate(prompt, *, model, system=None):  # type: ignore[no-untyped-def]
        captured["prompt"] = prompt
        captured["system"] = system
        return "ok"

    with patch("inclave_ollama.api.generate", side_effect=fake_generate):
        r = runner.invoke(app, ["ask", "what is the secret?"])
    assert r.exit_code == 0
    assert "the secret is 42" in captured["prompt"]  # type: ignore[operator]
    assert "privacy-first" in (captured["system"] or "")  # type: ignore[operator]


def test_ask_no_files_flag(fake_home: Path, tmp_path: Path) -> None:
    from unittest.mock import patch

    src = tmp_path / "x.txt"
    src.write_text("DO NOT INCLUDE")
    runner.invoke(app, ["models", "use", "m1"])
    runner.invoke(app, ["files", "add", str(src)])

    captured: dict[str, object] = {}

    def fake_generate(prompt, *, model, system=None):  # type: ignore[no-untyped-def]
        captured["prompt"] = prompt
        return "ok"

    with patch("inclave_ollama.api.generate", side_effect=fake_generate):
        r = runner.invoke(app, ["ask", "hi", "--no-files"])
    assert r.exit_code == 0
    assert "DO NOT INCLUDE" not in captured["prompt"]  # type: ignore[operator]
