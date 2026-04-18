"""Exception classes for the enclave_ollama package."""
from __future__ import annotations

from enclave_core.errors import EnclaveError


class OllamaError(EnclaveError):
    """Base exception for all Ollama-related errors."""
    pass


class OllamaUnavailableError(OllamaError):
    """Raised when the Ollama daemon is unreachable or not running."""
    pass
