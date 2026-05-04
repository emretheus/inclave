"""Tests for the drag-and-drop / paste path detector."""

from __future__ import annotations

from pathlib import Path

from enclave_cli.dropdetect import parse_drop


def test_single_path(tmp_path: Path) -> None:
    p = tmp_path / "doc.txt"
    p.write_text("x")
    out = parse_drop(str(p))
    assert out is not None
    assert out.paths == [p.resolve()]
    assert out.question == ""


def test_path_with_question(tmp_path: Path) -> None:
    p = tmp_path / "doc.txt"
    p.write_text("x")
    out = parse_drop(f"{p} what does this contain?")
    assert out is not None
    assert out.paths == [p.resolve()]
    assert out.question == "what does this contain?"


def test_multiple_paths_then_question(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    a.write_text("a")
    b = tmp_path / "b.csv"
    b.write_text("b")
    out = parse_drop(f"{a} {b} compare them")
    assert out is not None
    assert out.paths == [a.resolve(), b.resolve()]
    assert out.question == "compare them"


def test_quoted_path_with_spaces(tmp_path: Path) -> None:
    p = tmp_path / "with space.txt"
    p.write_text("x")
    out = parse_drop(f'"{p}" summarize')
    assert out is not None
    assert out.paths == [p.resolve()]
    assert out.question == "summarize"


def test_glob(tmp_path: Path) -> None:
    (tmp_path / "a.csv").write_text("1")
    (tmp_path / "b.csv").write_text("2")
    out = parse_drop(str(tmp_path / "*.csv"))
    assert out is not None
    assert len(out.paths) == 2


def test_text_only_no_paths() -> None:
    """A normal chat message with no leading path returns None."""
    assert parse_drop("look at /etc/hosts and tell me") is None
    assert parse_drop("just chatting") is None


def test_path_in_the_middle_is_chat(tmp_path: Path) -> None:
    """Paths must be at the very start of the line, not embedded."""
    p = tmp_path / "x.txt"
    p.write_text("x")
    assert parse_drop(f"please read {p}") is None


def test_nonexistent_path_falls_through() -> None:
    assert parse_drop("/no/such/file.pdf") is None


def test_slash_command_ignored() -> None:
    assert parse_drop("/help") is None


def test_empty() -> None:
    assert parse_drop("") is None
    assert parse_drop("   ") is None


def test_dedup(tmp_path: Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("x")
    out = parse_drop(f"{p} {p}")
    assert out is not None
    assert out.paths == [p.resolve()]
