#!/usr/bin/env bash
# Build the Python bridge into a self-contained binary with PyInstaller and stage
# it (plus the sandbox runtime) where Tauri's bundler expects it.
#
#   apps/desktop/scripts/build-sidecar.sh
#
# Output:
#   apps/desktop/src-tauri/binaries/inclave-bridge       (the sidecar binary)
#   apps/desktop/src-tauri/binaries/sandbox-runtime/     (the Seatbelt runtime venv)
#
# The Tauri config bundles these as app resources; sidecar.rs points
# INCLAVE_SANDBOX_RUNTIME at the staged runtime at launch.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DESKTOP="$REPO_ROOT/apps/desktop"
OUT="$DESKTOP/src-tauri/binaries"
RUNTIME_SRC="$REPO_ROOT/packages/sandbox/runtime"

echo "==> Ensuring sandbox runtime venv is built"
( cd "$RUNTIME_SRC" && uv sync )

echo "==> Building sidecar with PyInstaller"
cd "$REPO_ROOT"
uv run --with pyinstaller pyinstaller \
  --onedir \
  --name inclave-bridge \
  --noconfirm \
  --clean \
  --collect-all pandas \
  --collect-all numpy \
  --collect-all openpyxl \
  --collect-all pypdf \
  --collect-submodules inclave_bridge \
  --collect-submodules inclave_cli \
  --collect-submodules inclave_core \
  --collect-submodules inclave_ollama \
  --collect-submodules inclave_sandbox \
  --distpath "$DESKTOP/.pyi-dist" \
  --workpath "$DESKTOP/.pyi-build" \
  --specpath "$DESKTOP/.pyi-spec" \
  "$REPO_ROOT/packages/bridge/src/inclave_bridge/__main__.py"

echo "==> Staging into Tauri resources"
mkdir -p "$OUT"
rm -rf "$OUT/inclave-bridge.app" "$OUT/sandbox-runtime"
cp -R "$DESKTOP/.pyi-dist/inclave-bridge/." "$OUT/"
cp -R "$RUNTIME_SRC" "$OUT/sandbox-runtime"

echo "==> Done. Sidecar staged at $OUT"
