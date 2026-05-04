"""Unit tests for the demo chat REPL."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from inclave_cli.chat import run_chat
from inclave_core.errors import OllamaUnavailableError
from rich.console import Console


def _consoles() -> tuple[Console, io.StringIO, Console, io.StringIO]:
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    out = Console(file=out_buf, width=120, force_terminal=False, highlight=False)
    err = Console(file=err_buf, width=120, force_terminal=False, highlight=False)
    return out, out_buf, err, err_buf


def _fake_stream(text: str):  # type: ignore[no-untyped-def]
    def _gen(model, messages):  # type: ignore[no-untyped-def]
        yield from text

    return _gen


def _run(
    out: Console,
    err: Console,
    monkeypatch: pytest.MonkeyPatch,
    inputs: list[str],
) -> int:
    it = iter(inputs)
    monkeypatch.setattr("inclave_cli.chat.Console.input", lambda self, prompt="": next(it))
    return run_chat(out, err, model="m1", file_refs=[])


def test_help_and_exit(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out, out_buf, err, _ = _consoles()
    rc = _run(out, err, monkeypatch, ["/help", "/exit"])
    assert rc == 0
    assert "commands" in out_buf.getvalue()
    assert "drag & drop" in out_buf.getvalue()
    assert "bye" in out_buf.getvalue()


def test_bare_exit_quits(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out, out_buf, err, _ = _consoles()
    rc = _run(out, err, monkeypatch, ["exit"])
    assert rc == 0
    assert "bye" in out_buf.getvalue()


def test_bare_quit_quits(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out, out_buf, err, _ = _consoles()
    rc = _run(out, err, monkeypatch, ["quit"])
    assert rc == 0
    assert "bye" in out_buf.getvalue()


def test_unknown_slash(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out, _, err, err_buf = _consoles()
    _run(out, err, monkeypatch, ["/garbage", "/exit"])
    assert "unknown command" in err_buf.getvalue()


def test_clear_resets_history(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out, out_buf, err, _ = _consoles()
    with patch("inclave_cli.chat._stream_chat", _fake_stream("hello")):
        rc = _run(out, err, monkeypatch, ["hi", "/clear", "/exit"])
    assert rc == 0
    assert "hello" in out_buf.getvalue()
    assert "history cleared" in out_buf.getvalue()


def test_reset_wipes_files(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out, out_buf, err, _ = _consoles()
    _run(out, err, monkeypatch, ["/reset", "/exit"])
    assert "conversation and attached files cleared" in out_buf.getvalue()


def test_multi_turn_keeps_history(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out, _, err, _ = _consoles()
    captured: list[list[dict[str, str]]] = []

    def fake(model, messages):  # type: ignore[no-untyped-def]
        captured.append([dict(m) for m in messages])
        yield "ok"

    with patch("inclave_cli.chat._stream_chat", fake):
        _run(out, err, monkeypatch, ["one", "two", "/exit"])

    assert len(captured) == 2
    # First turn: system + first user
    assert captured[0][0]["role"] == "system"
    assert captured[0][1] == {"role": "user", "content": "one"}
    # Second turn: system + user1 + assistant1 + user2
    assert captured[1][-1] == {"role": "user", "content": "two"}
    assert {"role": "assistant", "content": "ok"} in captured[1]


def test_eof_exits_cleanly(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out, out_buf, err, _ = _consoles()

    def raise_eof(self, prompt=""):  # type: ignore[no-untyped-def]
        raise EOFError

    monkeypatch.setattr("inclave_cli.chat.Console.input", raise_eof)
    rc = run_chat(out, err, model="m1", file_refs=[])
    assert rc == 0
    assert "bye" in out_buf.getvalue()


def test_double_ctrl_c_exits(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out, out_buf, err, _ = _consoles()
    calls = {"n": 0}

    def stub(self, prompt=""):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        raise KeyboardInterrupt

    monkeypatch.setattr("inclave_cli.chat.Console.input", stub)
    rc = run_chat(out, err, model="m1", file_refs=[])
    assert rc == 0
    assert calls["n"] == 2
    assert "press Ctrl+C again" in out_buf.getvalue()


def test_ollama_unavailable_propagates(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out, _, err, err_buf = _consoles()

    def boom(model, messages):  # type: ignore[no-untyped-def]
        raise OllamaUnavailableError("Ollama is not running. Start it with: ollama serve")
        yield  # pragma: no cover

    with patch("inclave_cli.chat._stream_chat", boom):
        rc = _run(out, err, monkeypatch, ["hi"])
    assert rc == 3
    assert "Ollama is not running" in err_buf.getvalue()


def test_no_model_raises() -> None:
    from inclave_core import CLIError

    out, _, err, _ = _consoles()
    with pytest.raises(CLIError):
        run_chat(out, err, model="", file_refs=[])


def test_chat_command_invokes_repl(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from inclave_cli.main import app
    from typer.testing import CliRunner

    runner = CliRunner()
    runner.invoke(app, ["models", "use", "llama3.2"])

    called: dict[str, object] = {}

    def fake_run_chat(out_console, err_console, model, **kwargs):  # type: ignore[no-untyped-def]
        called["model"] = model
        called["kwargs"] = kwargs
        return 0

    monkeypatch.setattr("inclave_cli.chat.run_chat", fake_run_chat)
    result = runner.invoke(app, ["chat"])
    assert result.exit_code == 0
    assert called["model"] == "llama3.2"


def test_chat_no_model(fake_home: Path) -> None:
    from inclave_cli.main import app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(app, ["chat"])
    assert result.exit_code == 1
    assert "no model selected" in result.output


def test_file_attach_via_slash(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = fake_home / "doc.txt"
    src.write_text("hello world")

    out, out_buf, err, _ = _consoles()
    _run(out, err, monkeypatch, [f"/file {src}", "/files", "/exit"])
    output = out_buf.getvalue()
    assert "doc.txt" in output
    assert "attached" in output


def test_run_no_block(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out, _, err, err_buf = _consoles()
    _run(out, err, monkeypatch, ["/run", "/exit"])
    assert "no python code block" in err_buf.getvalue()


def test_run_executes_last_block(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When the model has emitted a python block, /run y → sandbox executes it."""
    from inclave_sandbox.api import ExecutionResult

    def fake(model, messages):  # type: ignore[no-untyped-def]
        yield "here you go:\n```python\nprint('hi')\n```\n"

    fake_exec = ExecutionResult(
        stdout="hi\n", stderr="", exit_code=0, timed_out=False, duration_ms=10
    )

    out, out_buf, err, _ = _consoles()
    with (
        patch("inclave_cli.chat._stream_chat", fake),
        patch("inclave_cli.chat.execute_python", return_value=fake_exec, create=True),
        patch("inclave_sandbox.execute_python", return_value=fake_exec),
    ):
        _run(out, err, monkeypatch, ["please write hi", "/run", "y", "/exit"])
    assert "stdout" in out_buf.getvalue()
    assert "hi" in out_buf.getvalue()
    assert "ran · " in out_buf.getvalue()


def test_run_declines(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(model, messages):  # type: ignore[no-untyped-def]
        yield "```python\nprint('boom')\n```"

    out, out_buf, err, _ = _consoles()
    with patch("inclave_cli.chat._stream_chat", fake):
        _run(out, err, monkeypatch, ["go", "/run", "n", "/exit"])
    assert "not running" in out_buf.getvalue()


def test_drop_path_attaches(
    fake_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pasting/dragging a bare path attaches it without needing /file."""
    src = tmp_path / "report.csv"
    src.write_text("a,b\n1,2\n")

    out, out_buf, err, _ = _consoles()
    _run(out, err, monkeypatch, [str(src), "/files", "/exit"])
    output = out_buf.getvalue()
    assert "+ report.csv" in output
    assert "1 new file attached" in output
    # /files lists it
    assert "report.csv" in output


def test_drop_multiple_paths(
    fake_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    a = tmp_path / "a.txt"
    a.write_text("a")
    b = tmp_path / "b.md"
    b.write_text("b")

    out, out_buf, err, _ = _consoles()
    _run(out, err, monkeypatch, [f"{a} {b}", "/exit"])
    output = out_buf.getvalue()
    assert "a.txt" in output and "b.md" in output
    assert "2 new files attached" in output


def test_model_command_lists_when_no_arg(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`/model` with no arg shows current + lists installed models."""
    from inclave_ollama.api import ModelInfo

    fake = [
        ModelInfo(name="m1", size_bytes=0, family="", parameter_count="", is_default=False),
        ModelInfo(name="m2", size_bytes=0, family="", parameter_count="", is_default=False),
    ]
    out, out_buf, err, _ = _consoles()
    with patch("inclave_cli.chat._list_local_model_names", return_value=["m1", "m2"]):
        _run(out, err, monkeypatch, ["/model", "/exit"])
    output = out_buf.getvalue()
    assert "current model: m1" in output
    assert "m1" in output and "m2" in output
    assert fake  # silence unused


def test_model_switch_to_known_model(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`/model m2` switches; subsequent prompts go to m2."""
    captured: dict[str, str] = {}

    def fake(model, messages):  # type: ignore[no-untyped-def]
        captured["model"] = model
        yield "ok"

    out, out_buf, err, _ = _consoles()
    with (
        patch("inclave_cli.chat._list_local_model_names", return_value=["m1", "m2"]),
        patch("inclave_cli.chat._stream_chat", fake),
    ):
        _run(out, err, monkeypatch, ["/model m2", "hi", "/exit"])
    assert "switched to m2" in out_buf.getvalue()
    assert captured["model"] == "m2"


def test_model_switch_unknown_model(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out, _, err, err_buf = _consoles()
    with patch("inclave_cli.chat._list_local_model_names", return_value=["m1"]):
        _run(out, err, monkeypatch, ["/model nope", "/exit"])
    assert "model not installed" in err_buf.getvalue()


def test_drop_path_plus_question_in_one_line(
    fake_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drop a file and ask in the same input — file is attached AND question is sent."""
    src = tmp_path / "data.txt"
    src.write_text("hello")

    captured: dict[str, str] = {}

    def fake(model, messages):  # type: ignore[no-untyped-def]
        # find the last user message and capture it
        for m in reversed(messages):
            if m["role"] == "user":
                captured["prompt"] = m["content"]
                break
        yield "answer"

    out, out_buf, err, _ = _consoles()
    with patch("inclave_cli.chat._stream_chat", fake):
        _run(out, err, monkeypatch, [f"{src} summarize this", "/exit"])
    assert "hello" in captured["prompt"]
    assert "summarize this" in captured["prompt"]
    assert "answer" in out_buf.getvalue()
