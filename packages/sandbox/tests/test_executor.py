import shutil
import sys
from pathlib import Path

import inclave_sandbox as sb
import pytest
from inclave_sandbox.errors import SandboxError
from inclave_sandbox.runtime import runtime_python


def _runtime_built() -> bool:
    try:
        runtime_python()
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.skipif(sys.platform != "darwin", reason="requires macOS"),
    pytest.mark.skipif(shutil.which("sandbox-exec") is None, reason="sandbox-exec not on PATH"),
    pytest.mark.skipif(
        not _runtime_built(),
        reason="runtime venv not built — cd packages/sandbox/runtime && uv sync",
    ),
]


def _policy(workdir: Path, **overrides: object) -> sb.SandboxPolicy:
    base: dict[str, object] = {
        "workdir": workdir,
        "cpu_seconds": 5,
        "memory_mb": 256,
        "wall_clock_seconds": 10,
    }
    base.update(overrides)
    return sb.SandboxPolicy(**base)  # type: ignore[arg-type]


def test_hello_world(workdir: Path) -> None:
    result = sb.execute_python("print('hello')", _policy(workdir))
    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.stdout.strip() == "hello"
    assert result.duration_ms >= 0


def test_non_zero_exit(workdir: Path) -> None:
    result = sb.execute_python("import sys; sys.exit(7)", _policy(workdir))
    assert result.exit_code == 7
    assert result.timed_out is False


def test_stderr_capture(workdir: Path) -> None:
    code = "import sys; sys.stderr.write('boom\\n'); sys.exit(0)"
    result = sb.execute_python(code, _policy(workdir))
    assert result.exit_code == 0
    assert "boom" in result.stderr


def test_wall_clock_timeout(workdir: Path) -> None:
    code = "import time; time.sleep(30)"
    result = sb.execute_python(code, _policy(workdir, wall_clock_seconds=2))
    assert result.timed_out is True
    assert result.duration_ms >= 1000


def test_workdir_writable(workdir: Path) -> None:
    code = "from pathlib import Path; Path('out.txt').write_text('ok')"
    result = sb.execute_python(code, _policy(workdir))
    assert result.exit_code == 0, result.stderr
    assert (workdir / "out.txt").read_text() == "ok"


def test_workdir_readable(workdir: Path) -> None:
    (workdir / "input.txt").write_text("hello from host")
    code = "from pathlib import Path; print(Path('input.txt').read_text())"
    result = sb.execute_python(code, _policy(workdir))
    assert result.exit_code == 0, result.stderr
    assert "hello from host" in result.stdout


def test_env_is_minimal(workdir: Path) -> None:
    code = "import json, os, sys; json.dump(sorted(os.environ.keys()), sys.stdout)"
    result = sb.execute_python(code, _policy(workdir))
    assert result.exit_code == 0, result.stderr
    import json

    keys = set(json.loads(result.stdout))
    assert "USER" not in keys
    assert "HOME" in keys
    assert "PATH" in keys


def test_validate_rejects_relative_workdir() -> None:
    with pytest.raises(SandboxError, match="absolute"):
        sb.execute_python("print('x')", sb.SandboxPolicy(workdir=Path("relative/dir")))


def test_validate_rejects_missing_workdir(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(SandboxError, match="does not exist"):
        sb.execute_python("print('x')", sb.SandboxPolicy(workdir=missing))


def test_validate_rejects_allow_network(workdir: Path) -> None:
    with pytest.raises(SandboxError, match="allow_network"):
        sb.execute_python("print('x')", _policy(workdir, allow_network=True))


def test_bundled_pandas_importable(workdir: Path) -> None:
    code = "import pandas; print(pandas.__version__)"
    result = sb.execute_python(code, _policy(workdir))
    assert result.exit_code == 0, result.stderr
    assert result.stdout.strip().count(".") >= 1
