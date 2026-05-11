"""Onboarding flows: ollama detection, model picker, default selection.

These tests never start a real ollama process or pull a real model — every
external side effect is mocked at the inclave_ollama / subprocess boundary.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from inclave_cli import onboarding
from inclave_core import OllamaUnavailableError, load_config
from rich.console import Console


def _consoles() -> tuple[Console, io.StringIO, Console, io.StringIO]:
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    out = Console(file=out_buf, width=120, force_terminal=False, highlight=False)
    err = Console(file=err_buf, width=120, force_terminal=False, highlight=False)
    return out, out_buf, err, err_buf


# ---------- ensure_dirs ----------


def test_ensure_dirs_is_idempotent(fake_home: Path) -> None:
    onboarding.ensure_dirs()
    onboarding.ensure_dirs()
    assert (fake_home / ".inclave" / "sessions").is_dir()
    assert (fake_home / ".inclave" / "log").is_dir()


# ---------- ensure_ollama_running ----------


def test_ollama_running_returns_silently(fake_home: Path) -> None:
    out, _, err, _ = _consoles()
    with patch("inclave_cli.onboarding._ollama_up", return_value=True):
        onboarding.ensure_ollama_running(out, err)  # no exception


def test_ollama_not_running_non_tty_raises(fake_home: Path) -> None:
    out, _, err, _ = _consoles()
    with (
        patch("inclave_cli.onboarding._ollama_up", return_value=False),
        patch("inclave_cli.onboarding._is_tty", return_value=False),
    ):
        with pytest.raises(OllamaUnavailableError):
            onboarding.ensure_ollama_running(out, err)


def test_ollama_not_installed_is_clear(fake_home: Path) -> None:
    out, _, err, err_buf = _consoles()
    with (
        patch("inclave_cli.onboarding._ollama_up", return_value=False),
        patch("inclave_cli.onboarding._is_tty", return_value=True),
        patch("inclave_cli.onboarding._ollama_installed", return_value=False),
    ):
        with pytest.raises(OllamaUnavailableError):
            onboarding.ensure_ollama_running(out, err)
    assert "brew install ollama" in err_buf.getvalue()


def test_ollama_user_picks_auto_start(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Default choice (1) spawns ollama serve and waits for it to come up."""
    out, out_buf, err, _ = _consoles()
    spawned: dict[str, bool] = {"called": False}

    def fake_spawn() -> None:
        spawned["called"] = True

    monkeypatch.setattr("inclave_cli.onboarding.Console.input", lambda self, prompt="": "1")
    with (
        patch("inclave_cli.onboarding._ollama_up", side_effect=[False, True]),
        patch("inclave_cli.onboarding._is_tty", return_value=True),
        patch("inclave_cli.onboarding._ollama_installed", return_value=True),
        patch("inclave_cli.onboarding._spawn_ollama_daemon", fake_spawn),
        patch("inclave_cli.onboarding._wait_for_ollama", return_value=True),
    ):
        onboarding.ensure_ollama_running(out, err)
    assert spawned["called"]
    assert "ollama up" in out_buf.getvalue()


def test_ollama_user_quits(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out, _, err, _ = _consoles()
    monkeypatch.setattr("inclave_cli.onboarding.Console.input", lambda self, prompt="": "q")
    with (
        patch("inclave_cli.onboarding._ollama_up", return_value=False),
        patch("inclave_cli.onboarding._is_tty", return_value=True),
        patch("inclave_cli.onboarding._ollama_installed", return_value=True),
    ):
        with pytest.raises(OllamaUnavailableError):
            onboarding.ensure_ollama_running(out, err)


def test_ollama_autostart_fails_is_actionable(
    fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If spawn succeeds but ollama never comes up, raise a clear error."""
    out, _, err, _ = _consoles()
    monkeypatch.setattr("inclave_cli.onboarding.Console.input", lambda self, prompt="": "1")
    with (
        patch("inclave_cli.onboarding._ollama_up", return_value=False),
        patch("inclave_cli.onboarding._is_tty", return_value=True),
        patch("inclave_cli.onboarding._ollama_installed", return_value=True),
        patch("inclave_cli.onboarding._spawn_ollama_daemon"),
        patch("inclave_cli.onboarding._wait_for_ollama", return_value=False),
    ):
        with pytest.raises(OllamaUnavailableError) as excinfo:
            onboarding.ensure_ollama_running(out, err)
    assert "ollama serve" in str(excinfo.value)


# ---------- ensure_default_model ----------


def test_existing_default_returns_silently(fake_home: Path) -> None:
    """If the default model is set and still installed, return it without prompting."""
    from inclave_core import set_config_value
    from inclave_ollama.api import ModelInfo

    set_config_value("default_model", "llama3.2")
    fake = [ModelInfo("llama3.2", 0, "", "", True)]
    out, _, err, _ = _consoles()
    chosen = onboarding.ensure_default_model(out, err, list_models_fn=lambda: fake)
    assert chosen == "llama3.2"


def test_no_models_offers_recommended_pull(
    fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """User picks option 1 → first recommended model is pulled + defaulted."""
    out, out_buf, err, _ = _consoles()
    monkeypatch.setattr("inclave_cli.onboarding.Console.input", lambda self, prompt="": "1")

    pull_calls: dict[str, str] = {}

    def fake_pull(name: str):  # type: ignore[no-untyped-def]
        pull_calls["name"] = name
        yield "downloading"
        yield "complete"

    monkeypatch.setattr("inclave_ollama.api.pull_model", fake_pull)
    with patch("inclave_cli.onboarding._is_tty", return_value=True):
        chosen = onboarding.ensure_default_model(out, err, list_models_fn=lambda: [])
    assert chosen == onboarding.RECOMMENDED_MODELS[0][0]
    assert pull_calls["name"] == onboarding.RECOMMENDED_MODELS[0][0]
    assert load_config().default_model == chosen
    assert "set as default" in out_buf.getvalue()


def test_no_models_non_tty_raises_clean_error(fake_home: Path) -> None:
    out, _, err, _ = _consoles()
    with patch("inclave_cli.onboarding._is_tty", return_value=False):
        with pytest.raises(OllamaUnavailableError) as excinfo:
            onboarding.ensure_default_model(out, err, list_models_fn=lambda: [])
    assert "ollama pull" in str(excinfo.value)


def test_models_exist_but_no_default_prompts_picker(
    fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from inclave_ollama.api import ModelInfo

    fake = [
        ModelInfo("m1", 0, "", "", False),
        ModelInfo("m2", 0, "", "", False),
    ]
    out, out_buf, err, _ = _consoles()
    monkeypatch.setattr("inclave_cli.onboarding.Console.input", lambda self, prompt="": "2")
    with patch("inclave_cli.onboarding._is_tty", return_value=True):
        chosen = onboarding.ensure_default_model(out, err, list_models_fn=lambda: fake)
    assert chosen == "m2"
    assert load_config().default_model == "m2"
    assert "default model: m2" in out_buf.getvalue()


def test_picker_accepts_free_text_model_name(
    fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """User can type 'other' then a name not in the recommended list."""
    inputs = iter(["other", "mistral:7b"])
    monkeypatch.setattr(
        "inclave_cli.onboarding.Console.input",
        lambda self, prompt="": next(inputs),
    )

    def fake_pull(name: str):  # type: ignore[no-untyped-def]
        yield "ok"

    monkeypatch.setattr("inclave_ollama.api.pull_model", fake_pull)
    out, _, err, _ = _consoles()
    with patch("inclave_cli.onboarding._is_tty", return_value=True):
        chosen = onboarding.ensure_default_model(out, err, list_models_fn=lambda: [])
    assert chosen == "mistral:7b"


def test_picker_quits_cleanly(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out, _, err, _ = _consoles()
    monkeypatch.setattr("inclave_cli.onboarding.Console.input", lambda self, prompt="": "q")
    with patch("inclave_cli.onboarding._is_tty", return_value=True):
        with pytest.raises(OllamaUnavailableError):
            onboarding.ensure_default_model(out, err, list_models_fn=lambda: [])


# ---------- preflight (the orchestrator) ----------


def test_preflight_happy_path(fake_home: Path) -> None:
    """All checks pass → returns the existing default."""
    from inclave_core import set_config_value
    from inclave_ollama.api import ModelInfo

    set_config_value("default_model", "llama3.2")
    out, _, err, _ = _consoles()
    with (
        patch("inclave_cli.onboarding._ollama_up", return_value=True),
        patch(
            "inclave_ollama.api.list_models",
            return_value=[ModelInfo("llama3.2", 0, "", "", True)],
        ),
    ):
        chosen = onboarding.preflight(out, err)
    assert chosen == "llama3.2"
