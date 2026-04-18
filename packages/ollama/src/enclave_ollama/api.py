"""Public API contract for Ollama model management and inference."""

from __future__ import annotations

import functools
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import httpx
import ollama
from enclave_core.config import load_config, save_config

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
        current_default = get_default()

        for m in response.get("models", []):
            details = m.get("details", {})
            models.append(
                ModelInfo(
                    name=m.get("name", ""),
                    size_bytes=m.get("size", 0),
                    family=details.get("family", ""),
                    parameter_count=details.get("parameter_size", ""),
                    is_default=(m.get("name", "") == current_default),
                )
            )
        return models
    except (httpx.ConnectError, ConnectionError) as e:
        raise OllamaUnavailableError("Ollama is not running. Start it with: ollama serve") from e
    except Exception as e:
        raise OllamaError(f"Failed to list models: {e}") from e


def pull_model(name: str) -> Iterator[str]:
    """
    Pulls a model from the Ollama registry.

    Yields:
        Human-readable progress strings (e.g., "downloading 4.7 GB").
    """
    try:
        response_stream = ollama.pull(name, stream=True)

        for chunk in response_stream:
            status = chunk.get("status", "")
            completed = chunk.get("completed")
            total = chunk.get("total")

            if completed is not None and total is not None and total > 0:
                yield f"{status} ({completed}/{total})"
            else:
                yield status

    except ollama.ResponseError as e:
        raise OllamaError(f"Failed to pull model: {e.error}") from e
    except Exception as e:
        raise OllamaError(f"Failed to pull model: {e}") from e


def remove_model(name: str) -> None:
    """Deletes a local model from the Ollama daemon."""
    try:
        ollama.delete(name)
    except ollama.ResponseError as e:
        raise OllamaError(f"Failed to remove model: {e.error}") from e
    except Exception as e:
        raise OllamaError(f"Failed to remove model: {e}") from e


def set_default(name: str) -> None:
    """Sets the default model in the Enclave global configuration."""
    try:
        config = load_config()
        config.default_model = name
        save_config(config)
    except Exception as e:
        raise OllamaError(f"Failed to set default model: {e}") from e


def get_default() -> str | None:
    """Retrieves the default model from the Enclave global configuration."""
    try:
        config = load_config()
        val = config.default_model
        return str(val) if val else None
    except Exception as e:
        raise OllamaError(f"Failed to get default model: {e}") from e


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
        content = response.get("message", {}).get("content", "")
        return str(content)
    except (httpx.ConnectError, ConnectionError) as e:
        raise OllamaUnavailableError("Ollama is not running. Start it with: ollama serve") from e
    except ollama.ResponseError as e:
        raise OllamaError(f"Ollama error: {e.error}") from e
    except Exception as e:
        raise OllamaError(f"Generation failed: {e}") from e


def stream(prompt: str, model: str = "") -> Iterator[str]:
    """
    Generates text from a model in a streaming fashion.

    Yields:
        Chunks of the generated text as they become available.
    """
    if not model:
        raise OllamaError("A model must be specified")

    try:
        response_stream = ollama.chat(
            model=model, messages=[{"role": "user", "content": prompt}], stream=True
        )

        for chunk in response_stream:
            if "message" in chunk and "content" in chunk["message"]:
                yield chunk["message"]["content"]

    except (httpx.ConnectError, ConnectionError) as e:
        raise OllamaUnavailableError("Ollama is not running. Start it with: ollama serve") from e
    except ollama.ResponseError as e:
        raise OllamaError(f"Ollama error: {e.error}") from e
    except Exception as e:
        raise OllamaError(f"Failed to generate text: {e}") from e


def requires_ollama[F: Callable[..., Any]](func: F) -> F:
    """
    Decorator that checks if the Ollama daemon is running before executing a function.
    Raises OllamaUnavailableError if the daemon is unreachable.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            httpx.get("http://127.0.0.1:11434/api/tags", timeout=2.0)
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise OllamaUnavailableError(
                "Ollama is not running. Start it with: ollama serve"
            ) from e
        return func(*args, **kwargs)

    return wrapper  # type: ignore
