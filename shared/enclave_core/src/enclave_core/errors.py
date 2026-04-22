class EnclaveError(Exception):
    """Base class for all enclave-* package errors.

    Subclassed per package (SandboxError, OllamaError, ConfigError, CLIError).
    The CLI catches EnclaveError at top level, prints `error.message`, and
    exits with a code mapped per subclass (see PROJECT_PLAN.md §15.2).
    """


class ConfigError(EnclaveError):
    """Raised when config is malformed, missing required fields, or cannot be read/written."""


class SandboxError(EnclaveError):
    """Raised by enclave_sandbox for execution, policy, or isolation failures."""


class OllamaError(EnclaveError):
    """Raised by enclave_ollama for model-related or API failures."""


class OllamaUnavailableError(OllamaError):
    """Raised when the Ollama daemon is not running or unreachable.

    Mapped to exit code 3 by the CLI (see PROJECT_PLAN.md §15.2).
    """


class CLIError(EnclaveError):
    """Raised by enclave_cli for user-facing command errors (bad input, etc.)."""
