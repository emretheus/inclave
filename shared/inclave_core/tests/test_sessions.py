"""Sessions: autosave + named save + load + list."""

from __future__ import annotations

from pathlib import Path

import pytest
from inclave_core import (
    LAST,
    CLIError,
    Session,
    list_sessions,
    load_session,
    save_session,
)


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def _mk(model: str = "m1", messages: list[dict[str, str]] | None = None) -> Session:
    return Session(
        model=model,
        workdir="/tmp",
        file_ids=["abcd1234"],
        messages=messages or [{"role": "user", "content": "hi"}],
    )


def test_save_and_load_last(fake_home: Path) -> None:
    save_session(_mk())
    s = load_session(LAST)
    assert s is not None
    assert s.model == "m1"
    assert s.file_ids == ["abcd1234"]
    assert s.messages[0]["content"] == "hi"
    assert s.saved_at  # populated on save


def test_load_missing_returns_none(fake_home: Path) -> None:
    assert load_session(LAST) is None
    assert load_session("nope") is None


def test_save_named_then_list(fake_home: Path) -> None:
    save_session(_mk(model="a"), name="alpha")
    save_session(_mk(model="b"), name="beta")
    save_session(_mk(model="last"))
    items = list_sessions()
    names = [n for n, _ in items]
    assert names[0] == LAST  # last sorts first when present
    assert {"alpha", "beta"} <= set(names)


def test_invalid_session_name(fake_home: Path) -> None:
    for bad in ("", "  ", "a/b", ".hidden", "x" * 61):
        with pytest.raises(CLIError):
            save_session(_mk(), name=bad)


def test_corrupt_session_raises(fake_home: Path) -> None:
    from inclave_core import sessions_dir
    from inclave_core.errors import ConfigError

    (sessions_dir() / "last.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_session(LAST)


def test_round_trip_keeps_message_shape(fake_home: Path) -> None:
    messages = [
        {"role": "system", "content": "you are inclave"},
        {"role": "user", "content": "two"},
        {"role": "assistant", "content": "ok"},
    ]
    save_session(_mk(messages=messages))
    s = load_session(LAST)
    assert s is not None
    assert s.messages == messages


def test_partial_dict_loads_with_defaults(fake_home: Path) -> None:
    import json

    from inclave_core import sessions_dir

    (sessions_dir() / "last.json").write_text(json.dumps({"model": "x"}), encoding="utf-8")
    s = load_session(LAST)
    assert s is not None
    assert s.model == "x"
    assert s.messages == []
    assert s.file_ids == []
