"""Enclave global configuration — load and persist user settings."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from enclave_core.errors import ConfigError


def enclave_dir() -> Path:
    """Returns ~/.enclave, creating it if missing."""
    d = Path.home() / ".enclave"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _config_path() -> Path:
    return enclave_dir() / "config.json"


def sessions_dir() -> Path:
    d = enclave_dir() / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_dir() -> Path:
    d = enclave_dir() / "log"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class EnclaveConfig:
    """Global Enclave configuration.

    Demo subset of PROJECT_PLAN §5.3. TOML migration is tracked separately.
    """

    default_model: str | None = field(default=None)
    sandbox_cpu_seconds: int = 30
    sandbox_memory_mb: int = 512
    auto_run: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "default_model": self.default_model,
            "sandbox_cpu_seconds": self.sandbox_cpu_seconds,
            "sandbox_memory_mb": self.sandbox_memory_mb,
            "auto_run": self.auto_run,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> EnclaveConfig:
        cfg = cls()
        dm = data.get("default_model")
        if dm is None or isinstance(dm, str):
            cfg.default_model = dm
        cs = data.get("sandbox_cpu_seconds")
        if isinstance(cs, int):
            cfg.sandbox_cpu_seconds = cs
        mm = data.get("sandbox_memory_mb")
        if isinstance(mm, int):
            cfg.sandbox_memory_mb = mm
        ar = data.get("auto_run")
        if isinstance(ar, bool):
            cfg.auto_run = ar
        return cfg


CONFIG_KEYS: tuple[str, ...] = (
    "default_model",
    "sandbox_cpu_seconds",
    "sandbox_memory_mb",
    "auto_run",
)


def load_config() -> EnclaveConfig:
    """Loads config from disk. Returns defaults if file does not exist."""
    path = _config_path()
    if not path.exists():
        return EnclaveConfig()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise ConfigError(f"config at {path} is unreadable: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError(f"config at {path} must be a JSON object")
    return EnclaveConfig.from_dict(data)


def save_config(config: EnclaveConfig) -> None:
    """Persists config to disk atomically."""
    path = _config_path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
    os.replace(tmp, path)


def set_config_value(key: str, value: str) -> EnclaveConfig:
    """Sets a single field by name. Coerces from string. Persists. Returns new config."""
    if key not in CONFIG_KEYS:
        raise ConfigError(f"unknown config key: {key!r}. valid keys: {', '.join(CONFIG_KEYS)}")
    cfg = load_config()
    if key == "default_model":
        cfg.default_model = value or None
    elif key == "sandbox_cpu_seconds":
        cfg.sandbox_cpu_seconds = _parse_int(key, value)
    elif key == "sandbox_memory_mb":
        cfg.sandbox_memory_mb = _parse_int(key, value)
    elif key == "auto_run":
        cfg.auto_run = _parse_bool(key, value)
    save_config(cfg)
    return cfg


def _parse_int(key: str, value: str) -> int:
    try:
        return int(value)
    except ValueError as e:
        raise ConfigError(f"{key} must be an integer, got {value!r}") from e


def _parse_bool(key: str, value: str) -> bool:
    v = value.strip().lower()
    if v in ("true", "1", "yes", "y", "on"):
        return True
    if v in ("false", "0", "no", "n", "off"):
        return False
    raise ConfigError(f"{key} must be a boolean, got {value!r}")
