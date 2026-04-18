"""Public API contract for Ollama model management and inference."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    """Represents a locally available Ollama model."""
    name: str
    size_bytes: int
    family: str
    parameter_count: str
    is_default: bool


def list_models() -> list[ModelInfo]:
    """Lists all downloaded models from the local Ollama daemon."""
    raise NotImplementedError("list_models is not yet implemented")


def pull_model(name: str) -> Iterator[str]:
    """
    Pulls a model from the Ollama registry.

    Yields:
        Human-readable progress strings (e.g., "downloading 4.7 GB").
    """
    raise NotImplementedError("pull_model is not yet implemented")


def remove_model(name: str) -> None:
    """Deletes a local model from the Ollama daemon."""
    raise NotImplementedError("remove_model is not yet implemented")


def set_default(name: str) -> None:
    """Sets the default model in the Enclave global configuration."""
    raise NotImplementedError("set_default is not yet implemented")


def get_default() -> str | None:
    """Retrieves the default model from the Enclave global configuration."""
    raise NotImplementedError("get_default is not yet implemented")


def generate(prompt: str, *, model: str | None = None, system: str | None = None) -> str:
    """
    Generates a complete, one-shot response from the specified model.
    """
    raise NotImplementedError("generate is not yet implemented")


def stream(prompt: str, *, model: str | None = None, system: str | None = None) -> Iterator[str]:
    """
    Generates a streaming response from the specified model.

    Yields:
        Tokens of the generated text as they arrive.
    """
    raise NotImplementedError("stream is not yet implemented")
