"""Platform-dispatch tests for api.execute_python.

These run on EVERY platform (no skipif), so the dispatch branch in api.py is
covered on macOS and Linux CI as well as Windows. We monkeypatch sys.platform
rather than the OS to exercise each branch in isolation.
"""

from pathlib import Path

import inclave_sandbox.api as api
import pytest
from inclave_sandbox.errors import SandboxError


def test_unsupported_platform_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("sys.platform", "freebsd13")
    policy = api.SandboxPolicy(workdir=tmp_path.resolve())
    with pytest.raises(SandboxError, match="does not support platform 'freebsd13'"):
        api.execute_python("print('x')", policy)


def test_darwin_dispatches_to_seatbelt_backend(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """darwin must route into executor.py. We stub the impl to avoid needing a
    real Seatbelt run, and assert the macOS module was the one selected."""
    import inclave_sandbox.executor as mac

    called: dict[str, object] = {}

    def fake_impl(code: str, policy: api.SandboxPolicy) -> api.ExecutionResult:
        called["code"] = code
        return api.ExecutionResult("", "", 0, False, 0)

    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr(mac, "execute_python_impl", fake_impl)
    api.execute_python("marker", api.SandboxPolicy(workdir=tmp_path.resolve()))
    assert called["code"] == "marker"
