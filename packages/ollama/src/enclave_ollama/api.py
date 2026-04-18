"""Public API contract for Ollama model management and inference."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import httpx
import ollama
from enclave_ollama.errors import OllamaError, OllamaUnavailableError


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
    try:
        response = ollama.list()
        models = []
        for m in response.get("models", []):
            details = m.get("details", {})
            models.append(
                ModelInfo(
                    name=m.get("name", ""),
                    size_bytes=m.get("size", 0),
                    family=details.get("family", ""),
                    parameter_count=details.get("parameter_size", ""),
                    is_default=False,  # Will be merged with config later
                )
            )
        return models
    except httpx.ConnectError as e:
        raise OllamaUnavailableError("Ollama is not running. Start it with: ollama serve") from e
    except Exception as e:
        raise OllamaError(f"Failed to list models: {e}") from e


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
    if not model:
        raise OllamaError("A model must be specified for generation.")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        response = ollama.chat(model=model, messages=messages)
        return response.get("message", {}).get("content", "")
    except httpx.ConnectError as e:
        raise OllamaUnavailableError("Ollama is not running. Start it with: ollama serve") from e
    except ollama.ResponseError as e:
        raise OllamaError(f"Ollama error: {e.error}") from e
    except Exception as e:
        raise OllamaError(f"Generation failed: {e}") from e


def stream(prompt: str, *, model: str | None = None, system: str | None = None) -> Iterator[str]:
    """
    Generates a streaming response from the specified model.

    Yields:
        Tokens of the generated text as they arrive.
    """
    raise NotImplementedError("stream is not yet implemented")
