import sys
from dataclasses import dataclass
from pathlib import Path

from inclave_sandbox.errors import SandboxError


@dataclass(frozen=True)
class SandboxPolicy:
    """Limits applied to a single sandboxed execution.

    workdir is the only readable/writable directory inside the jail. The CLI
    always passes Path.cwd() at invocation time (see PROJECT_PLAN.md §6).
    """

    workdir: Path
    allow_network: bool = False
    cpu_seconds: int = 30
    memory_mb: int = 512
    wall_clock_seconds: int = 60


@dataclass(frozen=True)
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    duration_ms: int


def execute_python(code: str, policy: SandboxPolicy) -> ExecutionResult:
    """Run Python source inside the sandbox. Returns stdout, stderr, etc.

    The concrete isolation backend is chosen per-platform. The macOS backend
    uses Seatbelt + rlimits; the Windows backend uses Job Objects. Both honor
    the same SandboxPolicy contract and return the same ExecutionResult. The
    backend module is imported lazily so platform-specific imports (e.g.
    ``resource`` on macOS, ``ctypes.windll`` on Windows) are never evaluated
    on the wrong OS.
    """
    if sys.platform == "darwin":
        from inclave_sandbox.executor import execute_python_impl
    elif sys.platform == "win32":
        from inclave_sandbox.executor_windows import execute_python_impl
    else:
        raise SandboxError(
            f"inclave-sandbox does not support platform {sys.platform!r}; "
            "supported platforms are macOS (darwin) and Windows (win32)."
        )

    return execute_python_impl(code, policy)


def execute_shell(command: str, policy: SandboxPolicy) -> ExecutionResult:
    """Run a shell command inside the sandbox. Implemented in M2."""
    raise NotImplementedError("execute_shell lands in M2")
