"""Tests for the local file workspace."""

from __future__ import annotations

from pathlib import Path

import pytest
from inclave_core.errors import CLIError
from inclave_core.workspace import (
    add_file,
    clear_workspace,
    find_file,
    list_files,
    remove_file,
)


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def test_add_copies_into_workspace(fake_home: Path) -> None:
    src = fake_home / "src.txt"
    src.write_text("hello")
    entry, was_new = add_file(src)
    assert was_new is True
    assert entry.kind == "text"
    assert entry.bytes == 5
    stored = entry.stored_path()
    assert stored.is_file()
    assert stored.read_text() == "hello"

    # Original deletion does not affect the workspace copy.
    src.unlink()
    assert stored.is_file()


def test_add_dedup_by_content(fake_home: Path) -> None:
    src = fake_home / "a.txt"
    src.write_text("same")
    e1, new1 = add_file(src)
    other = fake_home / "b.txt"
    other.write_text("same")
    e2, new2 = add_file(other)
    assert new1 is True and new2 is False
    assert e1.id == e2.id
    assert len(list_files()) == 1


def test_remove_by_id(fake_home: Path) -> None:
    src = fake_home / "x.md"
    src.write_text("# hi")
    entry, _ = add_file(src)
    removed = remove_file(entry.id)
    assert removed.id == entry.id
    assert list_files() == []


def test_remove_unknown_raises(fake_home: Path) -> None:
    with pytest.raises(CLIError):
        remove_file("nope")


def test_find_by_name(fake_home: Path) -> None:
    src = fake_home / "report.csv"
    src.write_text("a,b\n1,2\n")
    entry, _ = add_file(src)
    found = find_file("report.csv")
    assert found.id == entry.id


def test_clear(fake_home: Path) -> None:
    for name in ("a.txt", "b.txt", "c.txt"):
        p = fake_home / name
        p.write_text(name)
        add_file(p)
    removed = clear_workspace()
    assert removed == 3
    assert list_files() == []


def test_kind_detection(fake_home: Path) -> None:
    cases = {"a.py": "code", "a.csv": "csv", "a.xlsx": "xlsx", "a.pdf": "pdf", "a.bin": "other"}
    for name, expected_kind in cases.items():
        p = fake_home / name
        # distinct content per file, otherwise dedup returns the first entry
        p.write_bytes(name.encode())
        entry, _ = add_file(p)
        assert entry.kind == expected_kind, name
