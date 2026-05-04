"""Exception classes for the inclave_ollama package."""

from __future__ import annotations

from inclave_core.errors import InClaveError


class OllamaError(InClaveError):
    """Base exception for all Ollama-related errors."""

    pass


class OllamaUnavailableError(OllamaError):
    """Raised when the Ollama daemon is unreachable or not running."""

    pass
