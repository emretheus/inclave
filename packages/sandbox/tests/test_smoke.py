from dataclasses import FrozenInstanceError
from pathlib import Path

import enclave_sandbox as sb
import pytest
from enclave_core.errors import EnclaveError

PUBLIC_NAMES = (
    "SandboxPolicy",
    "ExecutionResult",
    "execute_python",
    "execute_shell",
    "SandboxError",
)


def test_public_api_exports() -> None:
    for name in PUBLIC_NAMES:
        assert hasattr(sb, name), f"missing public export: {name}"


def test_sandbox_error_is_enclave_error() -> None:
    assert issubclass(sb.SandboxError, EnclaveError)


def test_policy_defaults() -> None:
    p = sb.SandboxPolicy(workdir=Path("/tmp"))
    assert p.workdir == Path("/tmp")
    assert p.allow_network is False
    assert p.cpu_seconds == 30
    assert p.memory_mb == 512
    assert p.wall_clock_seconds == 60


def test_policy_is_frozen() -> None:
    p = sb.SandboxPolicy(workdir=Path("/tmp"))
    with pytest.raises(FrozenInstanceError):
        p.workdir = Path("/elsewhere")  # type: ignore[misc]


def test_execution_result_construction() -> None:
    r = sb.ExecutionResult(stdout="hi", stderr="", exit_code=0, timed_out=False, duration_ms=12)
    assert r.stdout == "hi"
    assert r.exit_code == 0
    assert r.timed_out is False


def test_execute_shell_stub_raises() -> None:
    with pytest.raises(NotImplementedError):
        sb.execute_shell("echo x", sb.SandboxPolicy(workdir=Path("/tmp")))
