"""Handler-level tests for models / sessions / system with engine mocks."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from inclave_bridge.events import EventEmitter
from inclave_bridge.handlers import models as models_h
from inclave_bridge.handlers import sessions as sessions_h
from inclave_bridge.handlers import system as system_h
from inclave_ollama.api import ModelInfo


def test_models_list_includes_vram_flag(fake_home: Path) -> None:
    fake = [ModelInfo("m1", 1_000_000, "llama", "7B", True)]
    with (
        patch("inclave_bridge.handlers.models.list_models", return_value=fake),
        patch("inclave_bridge.handlers.models.is_model_fully_vram_compatible", return_value=True),
    ):
        out = models_h.list_({})
    assert out[0]["name"] == "m1"
    assert out[0]["vram_ok"] is True


def test_models_pull_emits_progress(fake_home: Path) -> None:
    captured: list[dict[str, Any]] = []
    emitter = EventEmitter(lambda frame: captured.append(frame))

    def fake_pull(name):  # type: ignore[no-untyped-def]
        yield "downloading (50/100)"
        yield "verifying"

    with patch("inclave_bridge.handlers.models.pull_model", fake_pull):
        res = models_h.pull({"name": "m1"}, emitter)

    assert res["pulled"] is True
    progress = [c for c in captured if c["method"] == "models.pull_progress"]
    assert progress[0]["params"]["completed"] == 50
    assert progress[0]["params"]["total"] == 100
    assert progress[1]["params"]["status"] == "verifying"


def test_sessions_save_load_delete_roundtrip(fake_home: Path) -> None:
    session_data = {
        "model": "m1",
        "workdir": "",
        "file_ids": [],
        "messages": [{"role": "user", "content": "hi"}],
    }
    sessions_h.save({"name": "mine", "session": session_data})
    loaded = sessions_h.load({"name": "mine"})
    assert loaded["model"] == "m1"
    assert sessions_h.delete({"name": "mine"})["deleted"] is True


def test_system_status_shape(fake_home: Path) -> None:
    with (
        patch("inclave_bridge.handlers.system._ollama_up", return_value=True),
        patch("inclave_bridge.handlers.system.get_total_ram_gb", return_value=16.0),
    ):
        st = system_h.status({})
    assert st["ollama_running"] is True
    assert st["ram_gb"] == 16.0
    assert "sandbox_ok" in st
