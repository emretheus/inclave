"""Enclave global configuration — load and persist user settings."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


def _config_path() -> Path:
    """Returns the path to the Enclave config file (~/.enclave/config.json)."""
    config_dir = Path.home() / ".enclave"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.json"


@dataclass
class EnclaveConfig:
    """Global Enclave configuration."""

    default_model: str | None = field(default=None)

    def to_dict(self) -> dict[str, object]:
        return {"default_model": self.default_model}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> EnclaveConfig:
        return cls(default_model=data.get("default_model"))  # type: ignore[arg-type]


def load_config() -> EnclaveConfig:
    """Loads config from disk. Returns defaults if file does not exist."""
    path = _config_path()
    if not path.exists():
        return EnclaveConfig()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return EnclaveConfig.from_dict(data)
    except (json.JSONDecodeError, OSError):
        return EnclaveConfig()


def save_config(config: EnclaveConfig) -> None:
    """Persists config to disk."""
    path = _config_path()
    path.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
