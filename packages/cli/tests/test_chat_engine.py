"""Tests for the headless chat engine (event-yielding turn loop)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from inclave_cli import chat_engine as engine
from inclave_core import InClaveConfig
from inclave_core.errors import OllamaUnavailableError


def _fake_stream(text: str):  # type: ignore[no-untyped-def]
    def _gen(model, messages):  # type: ignore[no-untyped-def]
        yield from text

    return _gen


def test_python_blocks_detection() -> None:
    content = "text\n```python\nprint('hi')\n```\nmore"
    assert engine.python_blocks_in(content) == ["print('hi')"]


def test_tagless_python_block_detected() -> None:
    content = "```\nimport os\nprint(os.getcwd())\n```"
    assert engine.python_blocks_in(content) == ["import os\nprint(os.getcwd())"]


def test_tagless_non_python_block_ignored() -> None:
    content = "```\njust prose, no code\n```"
    assert engine.python_blocks_in(content) == []


def test_bash_block_ignored() -> None:
    content = "```bash\nrm -rf /\n```"
    assert engine.python_blocks_in(content) == []


def test_run_turn_emits_token_and_message_done(fake_home: Path) -> None:
    messages: list[dict[str, str]] = []
    turn = engine.TurnConfig(model="m1", cfg=InClaveConfig())
    events = list(engine.run_turn(messages, "hi", turn, stream_fn=_fake_stream("hello")))
    kinds = [e.kind for e in events]
    assert "token" in kinds
    assert "message_done" in kinds
    assert kinds[-1] == "turn_done"
    # message committed to history
    assert messages[-1] == {"role": "assistant", "content": "hello"}


def test_run_turn_inserts_system_prompt_first(fake_home: Path) -> None:
    messages: list[dict[str, str]] = []
    turn = engine.TurnConfig(model="m1", cfg=InClaveConfig())
    list(engine.run_turn(messages, "hi", turn, stream_fn=_fake_stream("ok")))
    assert messages[0]["role"] == "system"
    assert messages[1] == {"role": "user", "content": "hi"}


def test_run_turn_ollama_unavailable_emits_error(fake_home: Path) -> None:
    def boom(model, messages):  # type: ignore[no-untyped-def]
        raise OllamaUnavailableError("Ollama is not running. Start it with: ollama serve")
        yield  # pragma: no cover

    messages: list[dict[str, str]] = []
    turn = engine.TurnConfig(model="m1", cfg=InClaveConfig())
    events = list(engine.run_turn(messages, "hi", turn, stream_fn=boom))
    errs = [e for e in events if isinstance(e, engine.ErrorEvent)]
    assert errs
    assert errs[0].code == "ollama_unavailable"
    # user message dropped from history so it isn't poisoned
    assert not any(m["role"] == "user" for m in messages)


def test_auto_run_loop_runs_sandbox_and_feeds_back(fake_home: Path) -> None:
    from inclave_sandbox.api import ExecutionResult

    streams = iter(
        [
            "```python\nprint('hi')\n```",
            "the script printed hi.",
        ]
    )

    def fake(model, messages):  # type: ignore[no-untyped-def]
        yield from next(streams)

    fake_exec = ExecutionResult(
        stdout="hi\n", stderr="", exit_code=0, timed_out=False, duration_ms=10
    )

    messages: list[dict[str, str]] = []
    turn = engine.TurnConfig(model="m1", cfg=InClaveConfig())
    with patch("inclave_sandbox.execute_python", return_value=fake_exec):
        events = list(engine.run_turn(messages, "go", turn, stream_fn=fake))

    kinds = [e.kind for e in events]
    assert "run_start" in kinds
    assert "run_output" in kinds
    run_out = next(e for e in events if isinstance(e, engine.RunOutputEvent))
    assert run_out.stdout == "hi\n"
    assert run_out.exit_code == 0
    # follow-up summary committed
    assert any(m["content"] == "the script printed hi." for m in messages)


def test_run_last_block_no_code(fake_home: Path) -> None:
    turn = engine.TurnConfig(model="m1", cfg=InClaveConfig())
    events = list(engine.run_last_block([], turn))
    assert any(isinstance(e, engine.ErrorEvent) and e.code == "no_code" for e in events)


def test_format_sandbox_observation_truncates() -> None:
    outcome = engine._SandboxOutcome(
        stdout="x" * 5000, stderr="", exit_code=0, duration_ms=1, timed_out=False
    )
    obs = engine.format_sandbox_observation(outcome)
    assert "truncated" in obs
    assert "exit 0" in obs


def test_format_sandbox_observation_timeout() -> None:
    outcome = engine._SandboxOutcome(
        stdout="", stderr="", exit_code=-9, duration_ms=1, timed_out=True
    )
    obs = engine.format_sandbox_observation(outcome)
    assert "TIMED OUT" in obs
