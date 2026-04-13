from __future__ import annotations

import os
import resource
import shutil
import signal
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from enclave_sandbox.api import ExecutionResult, SandboxPolicy
from enclave_sandbox.errors import SandboxError
from enclave_sandbox.profile import default_profile_path
from enclave_sandbox.runtime import python_install_root, runtime_python

SANDBOX_EXEC = "sandbox-exec"
MAX_OUTPUT_FILE_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_OPEN_FILES = 256


def _build_env(workdir: Path) -> dict[str, str]:
    """Return a minimal, predictable environment for the jailed process."""
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(workdir),
        "TMPDIR": str(workdir),
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
    }


def _make_preexec(policy: SandboxPolicy) -> Callable[[], None]:
    """Return a callable to apply rlimits in the child before exec."""
    cpu = policy.cpu_seconds
    mem_bytes = policy.memory_mb * 1024 * 1024

    def _preexec() -> None:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
        try:
            resource.setrlimit(resource.RLIMIT_DATA, (mem_bytes, mem_bytes))
        except (ValueError, OSError):
            pass
        try:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except (ValueError, OSError):
            pass
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_FILE_BYTES, MAX_OUTPUT_FILE_BYTES))
        resource.setrlimit(resource.RLIMIT_NOFILE, (MAX_OPEN_FILES, MAX_OPEN_FILES))

    return _preexec


def _validate(policy: SandboxPolicy) -> None:
    if shutil.which(SANDBOX_EXEC) is None:
        raise SandboxError(f"{SANDBOX_EXEC} not found on PATH. enclave-sandbox requires macOS.")
    if not policy.workdir.is_absolute():
        raise SandboxError(f"policy.workdir must be absolute, got {policy.workdir!r}")
    if not policy.workdir.is_dir():
        raise SandboxError(f"policy.workdir does not exist: {policy.workdir}")
    if policy.allow_network:
        raise SandboxError("allow_network=True is not supported in v0.1")


def _run(
    cmd: list[str],
    *,
    policy: SandboxPolicy,
) -> ExecutionResult:
    env = _build_env(policy.workdir)
    started = time.monotonic()
    timed_out = False

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(policy.workdir),
        preexec_fn=_make_preexec(policy),
        start_new_session=True,
        close_fds=True,
    )
    try:
        stdout_b, stderr_b = proc.communicate(timeout=policy.wall_clock_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout_b, stderr_b = proc.communicate()

    duration_ms = int((time.monotonic() - started) * 1000)
    return ExecutionResult(
        stdout=stdout_b.decode("utf-8", errors="replace"),
        stderr=stderr_b.decode("utf-8", errors="replace"),
        exit_code=proc.returncode if not timed_out else -signal.SIGKILL,
        timed_out=timed_out,
        duration_ms=duration_ms,
    )


def execute_python_impl(code: str, policy: SandboxPolicy) -> ExecutionResult:
    """Concrete implementation. Public entry is enclave_sandbox.api.execute_python."""
    _validate(policy)
    profile = default_profile_path()
    py = runtime_python()
    runtime_dir = py.parent.parent  # .venv/bin/python3 → .venv (read-allow root)
    install_root = python_install_root()

    cmd = [
        SANDBOX_EXEC,
        "-f",
        str(profile),
        "-D",
        f"WORKDIR={policy.workdir}",
        "-D",
        f"RUNTIME={runtime_dir}",
        "-D",
        f"PYTHON_HOME={install_root}",
        str(py),
        "-I",  # isolated mode: ignore PYTHON* env vars and user site-packages
        "-c",
        code,
    ]
    return _run(cmd, policy=policy)
