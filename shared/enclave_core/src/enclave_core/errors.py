class EnclaveError(Exception):
    """Base class for all enclave-* package errors.

    Subclassed per package (SandboxError, OllamaError, ConfigError, CLIError).
    The CLI catches EnclaveError at top level, prints `error.message`, and
    exits with a code mapped per subclass (see PROJECT_PLAN.md §15.2).
    """
