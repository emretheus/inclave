"""Unit tests for the demo CLI commands.

Ollama and sandbox calls are mocked — these tests run without a daemon or macOS sandbox.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from enclave_cli.main import app
from enclave_core.errors import OllamaUnavailableError
from enclave_ollama.api import ModelInfo
from enclave_sandbox.api import ExecutionResult
from typer.testing import CliRunner

runner = CliRunner()


def test_init_creates_dirs(fake_home: Path) -> None:
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.output
    assert (fake_home / ".enclave").is_dir()
    assert (fake_home / ".enclave" / "sessions").is_dir()
    assert (fake_home / ".enclave" / "log").is_dir()


def test_init_idempotent(fake_home: Path) -> None:
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0


def test_config_show_defaults(fake_home: Path) -> None:
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "default_model" in result.output
    assert "sandbox_cpu_seconds" in result.output


def test_config_set_and_show(fake_home: Path) -> None:
    r1 = runner.invoke(app, ["config", "set", "default_model", "llama3.2"])
    assert r1.exit_code == 0
    r2 = runner.invoke(app, ["config", "set", "sandbox_cpu_seconds", "60"])
    assert r2.exit_code == 0
    r3 = runner.invoke(app, ["config", "set", "auto_run", "true"])
    assert r3.exit_code == 0
    show = runner.invoke(app, ["config", "show"])
    assert "llama3.2" in show.output
    assert "60" in show.output
    assert "True" in show.output


def test_config_set_unknown_key(fake_home: Path) -> None:
    result = runner.invoke(app, ["config", "set", "garbage", "x"])
    assert result.exit_code == 2  # EXIT_CONFIG
    assert "unknown config key" in result.output


def test_config_set_bad_int(fake_home: Path) -> None:
    result = runner.invoke(app, ["config", "set", "sandbox_cpu_seconds", "not-a-number"])
    assert result.exit_code == 2


def test_models_use_writes_default(fake_home: Path) -> None:
    result = runner.invoke(app, ["models", "use", "llama3.2"])
    assert result.exit_code == 0
    show = runner.invoke(app, ["config", "show"])
    assert "llama3.2" in show.output


def test_models_list_renders_table(fake_home: Path) -> None:
    fake = [
        ModelInfo(
            name="llama3.2",
            size_bytes=4_700_000_000,
            family="llama",
            parameter_count="3B",
            is_default=True,
        ),
    ]
    with patch("enclave_ollama.api.list_models", return_value=fake):
        result = runner.invoke(app, ["models", "list"])
    assert result.exit_code == 0
    assert "llama3.2" in result.output


def test_models_list_ollama_unavailable(fake_home: Path) -> None:
    with patch(
        "enclave_ollama.api.list_models",
        side_effect=OllamaUnavailableError("Ollama is not running. Start it with: ollama serve"),
    ):
        result = runner.invoke(app, ["models", "list"])
    assert result.exit_code == 3  # EXIT_OLLAMA_UNAVAILABLE
    assert "Ollama is not running" in result.output


def test_ask_without_model_fails(fake_home: Path) -> None:
    result = runner.invoke(app, ["ask", "hello"])
    assert result.exit_code == 1
    assert "no model selected" in result.output


def test_ask_calls_generate(fake_home: Path) -> None:
    runner.invoke(app, ["models", "use", "llama3.2"])
    with patch("enclave_ollama.api.generate", return_value="hi there") as gen:
        result = runner.invoke(app, ["ask", "hello"])
    assert result.exit_code == 0
    assert "hi there" in result.output
    # workspace empty → prompt is just the question; system prompt is attached
    gen.assert_called_once()
    args, kwargs = gen.call_args
    assert args == ("hello",)
    assert kwargs["model"] == "llama3.2"
    assert "privacy-first" in kwargs["system"]


def test_run_missing_file(fake_home: Path) -> None:
    result = runner.invoke(app, ["run", "/no/such/file.py"])
    assert result.exit_code == 1
    assert "file not found" in result.output


def test_run_executes(fake_home: Path, tmp_path: Path) -> None:
    script = tmp_path / "hello.py"
    script.write_text("print('hi')")
    fake_result = ExecutionResult(
        stdout="hi\n",
        stderr="",
        exit_code=0,
        timed_out=False,
        duration_ms=42,
    )
    with patch("enclave_sandbox.execute_python", return_value=fake_result):
        result = runner.invoke(app, ["run", str(script)])
    assert result.exit_code == 0
    assert "hi" in result.output
    assert "exit 0" in result.output


def test_run_propagates_sandbox_failure(fake_home: Path, tmp_path: Path) -> None:
    script = tmp_path / "boom.py"
    script.write_text("raise SystemExit(2)")
    fake_result = ExecutionResult(
        stdout="",
        stderr="boom",
        exit_code=2,
        timed_out=False,
        duration_ms=10,
    )
    with patch("enclave_sandbox.execute_python", return_value=fake_result):
        result = runner.invoke(app, ["run", str(script)])
    assert result.exit_code == 4  # EXIT_SANDBOX
