import os
from pathlib import Path

from inclave_sandbox.errors import SandboxError

RUNTIME_DIR_NAME = "runtime"
VENV_NAME = ".venv"

# When the engine is bundled inside a desktop app (PyInstaller / Tauri), the
# sandbox runtime can't be located relative to this source file. The bundler
# sets INCLAVE_SANDBOX_RUNTIME to the packaged runtime directory.
RUNTIME_ENV = "INCLAVE_SANDBOX_RUNTIME"


def runtime_root() -> Path:
    """Absolute path to the sandbox runtime/ directory, regardless of how the
    engine was installed (editable checkout, wheel, or app bundle).

    Resolution order:
      1. $INCLAVE_SANDBOX_RUNTIME — set by the desktop bundler.
      2. packages/sandbox/runtime/ relative to this file — dev / editable.
      3. <pkg>/runtime/ — wheel-installed layout.
    """
    override = os.environ.get(RUNTIME_ENV)
    if override:
        path = Path(override).expanduser()
        if path.is_dir():
            return path
        raise SandboxError(f"{RUNTIME_ENV} points at a missing directory: {path}")

    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent.parent / RUNTIME_DIR_NAME,  # dev / editable
        here.parent / RUNTIME_DIR_NAME,  # wheel-installed (if ever bundled)
    ]
    for path in candidates:
        if path.is_dir():
            return path
    raise SandboxError(
        f"sandbox runtime directory not found. Looked in: {[str(c) for c in candidates]} "
        f"(set {RUNTIME_ENV} when running from a bundle)"
    )


def runtime_python() -> Path:
    """Absolute path to the bundled Python interpreter inside the runtime venv.

    Raises SandboxError with a build hint if the venv hasn't been created yet.
    """
    venv = runtime_root() / VENV_NAME
    py = venv / "bin" / "python3"
    if not py.is_file():
        raise SandboxError(
            f"sandbox runtime venv not built. Build it with:\n  cd {runtime_root()} && uv sync"
        )
    return py


def python_install_root() -> Path:
    """Directory containing the *real* CPython install (after symlink resolution).

    The venv's `bin/python3` is typically a symlink chain into uv's managed
    Python store (e.g. ~/.local/share/uv/python/cpython-3.13.x-...). Seatbelt
    resolves symlinks before checking permissions, so the profile must allow
    read+exec on this directory too.
    """
    real = runtime_python().resolve()
    return real.parent.parent  # .../bin/python3.13 → .../bin → install root
