from dataclasses import dataclass
from pathlib import Path


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
    """Run Python source inside the sandbox. Returns stdout, stderr, etc."""
    from enclave_sandbox.executor import execute_python_impl

    return execute_python_impl(code, policy)


def execute_shell(command: str, policy: SandboxPolicy) -> ExecutionResult:
    """Run a shell command inside the sandbox. Implemented in M2."""
    raise NotImplementedError("execute_shell lands in M2")
