from pathlib import Path

from enclave_sandbox.errors import SandboxError

DEFAULT_PROFILE_NAME = "default.sb"


def default_profile_path() -> Path:
    """Return the absolute path to the bundled default Seatbelt profile.

    Profiles ship under packages/sandbox/profiles/ (sibling of src/). For
    editable installs (uv sync) this resolves directly from the source tree.
    A wheel build maps the same files into the installed package; the
    fallback below covers that case.
    """
    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent.parent / "profiles" / DEFAULT_PROFILE_NAME,  # dev / editable
        here.parent / "profiles" / DEFAULT_PROFILE_NAME,  # wheel-installed
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise SandboxError(
        f"default sandbox profile not found. Looked in: {[str(c) for c in candidates]}"
    )
