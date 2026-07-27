"""Unit tests for the InClaveConfig load/save round-trip and set_config_value."""

from __future__ import annotations

from pathlib import Path

import pytest
from inclave_core.config import (
    InClaveConfig,
    load_config,
    save_config,
    set_config_value,
)
from inclave_core.errors import ConfigError


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def test_defaults_when_missing(fake_home: Path) -> None:
    cfg = load_config()
    assert cfg.default_model is None
    assert cfg.sandbox_cpu_seconds == 30
    assert cfg.sandbox_memory_mb == 512
    assert cfg.auto_run is False
    assert cfg.num_ctx == 32768


def test_round_trip(fake_home: Path) -> None:
    cfg = InClaveConfig(
        default_model="llama3.2",
        sandbox_cpu_seconds=42,
        sandbox_memory_mb=1024,
        auto_run=True,
        num_ctx=16384,
    )
    save_config(cfg)
    loaded = load_config()
    assert loaded == cfg


def test_set_known_keys(fake_home: Path) -> None:
    set_config_value("default_model", "llama3.2")
    set_config_value("sandbox_cpu_seconds", "60")
    set_config_value("auto_run", "true")
    cfg = load_config()
    assert cfg.default_model == "llama3.2"
    assert cfg.sandbox_cpu_seconds == 60
    assert cfg.auto_run is True


def test_set_unknown_key_raises(fake_home: Path) -> None:
    with pytest.raises(ConfigError, match="unknown config key"):
        set_config_value("garbage", "x")


def test_set_bad_int_raises(fake_home: Path) -> None:
    with pytest.raises(ConfigError, match="must be an integer"):
        set_config_value("sandbox_cpu_seconds", "abc")


def test_set_bad_bool_raises(fake_home: Path) -> None:
    with pytest.raises(ConfigError, match="must be a boolean"):
        set_config_value("auto_run", "maybe")


def test_set_num_ctx(fake_home: Path) -> None:
    set_config_value("num_ctx", "8192")
    assert load_config().num_ctx == 8192


def test_num_ctx_below_minimum_raises(fake_home: Path) -> None:
    """A tiny context silently evicts the system prompt — refuse it loudly."""
    with pytest.raises(ConfigError, match="must be at least 2048"):
        set_config_value("num_ctx", "512")


def test_num_ctx_ignores_bool_from_disk(fake_home: Path) -> None:
    """bool is an int subclass; `true` must not silently become num_ctx=1."""
    cfg_path = fake_home / ".inclave" / "config.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text('{"num_ctx": true}')
    assert load_config().num_ctx == 32768


def test_corrupt_json_raises(fake_home: Path) -> None:
    cfg_path = fake_home / ".inclave" / "config.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text("{not json")
    with pytest.raises(ConfigError):
        load_config()
