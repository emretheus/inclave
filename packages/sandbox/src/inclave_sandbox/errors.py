from inclave_core.errors import InClaveError


class SandboxError(InClaveError):
    """Raised when sandboxed execution fails to set up or is denied by policy.

    A timeout or non-zero exit from the sandboxed process is NOT a SandboxError
    — those are reported via ExecutionResult fields (timed_out, exit_code).
    SandboxError is for failures of the sandbox itself: profile load failure,
    sandbox-exec missing, runtime venv missing, etc.
    """
