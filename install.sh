#!/usr/bin/env bash
#
# Enclave Code installer
#
#   curl -fsSL https://raw.githubusercontent.com/caelusway/enclave-code/master/install.sh | sh
#
# What this does:
#   1. Refuses to run on anything other than macOS (sandbox is macOS-only).
#   2. Installs `uv` if it isn't already on PATH.
#   3. Clones (or updates) the repo into ~/.cache/enclave-code-src.
#   4. Installs the `enclave` console script via `uv tool install --from`.
#   5. Tells you what to do next.
#
# It does NOT install Ollama for you — that's a deliberate choice so you stay
# in control of your model setup. Run `brew install ollama && ollama serve`
# separately when you're ready.

set -euo pipefail

REPO_URL="https://github.com/caelusway/enclave-code.git"
SRC_DIR="${HOME}/.cache/enclave-code-src"
BRANCH="${ENCLAVE_BRANCH:-master}"

# ---------- pretty output ----------
if [ -t 1 ]; then
    BOLD=$(printf '\033[1m')
    DIM=$(printf '\033[2m')
    GREEN=$(printf '\033[32m')
    YELLOW=$(printf '\033[33m')
    RED=$(printf '\033[31m')
    RESET=$(printf '\033[0m')
else
    BOLD=""; DIM=""; GREEN=""; YELLOW=""; RED=""; RESET=""
fi

step() { printf "%s•%s %s\n" "$BOLD" "$RESET" "$*"; }
ok()   { printf "%s✓%s %s\n" "$GREEN" "$RESET" "$*"; }
warn() { printf "%s!%s %s\n" "$YELLOW" "$RESET" "$*"; }
die()  { printf "%s✗%s %s\n" "$RED" "$RESET" "$*" >&2; exit 1; }

# ---------- preflight ----------
step "Checking platform"
if [ "$(uname -s)" != "Darwin" ]; then
    die "Enclave Code requires macOS (Seatbelt sandbox). Detected: $(uname -s)."
fi
ok "macOS detected"

# ---------- uv ----------
if ! command -v uv >/dev/null 2>&1; then
    step "Installing uv"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # uv installs to ~/.local/bin or ~/.cargo/bin; pick it up for this session.
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if ! command -v uv >/dev/null 2>&1; then
        die "uv install completed but \`uv\` is still not on PATH. Open a new shell and re-run this script."
    fi
    ok "uv installed"
else
    ok "uv already installed ($(uv --version 2>/dev/null | head -n1))"
fi

# ---------- git ----------
if ! command -v git >/dev/null 2>&1; then
    die "git is required but not found. Install Xcode Command Line Tools: xcode-select --install"
fi

# ---------- source ----------
if [ -d "$SRC_DIR/.git" ]; then
    step "Updating $SRC_DIR"
    git -C "$SRC_DIR" fetch --quiet origin "$BRANCH"
    git -C "$SRC_DIR" checkout --quiet "$BRANCH"
    git -C "$SRC_DIR" reset --hard --quiet "origin/$BRANCH"
else
    step "Cloning into $SRC_DIR"
    rm -rf "$SRC_DIR"
    git clone --quiet --branch "$BRANCH" "$REPO_URL" "$SRC_DIR"
fi
ok "Source ready"

# ---------- install ----------
step "Installing enclave-cli"
# --force so re-running upgrades cleanly.
uv tool install --quiet --force --from "$SRC_DIR/packages/cli" enclave-cli
ok "enclave-cli installed"

# ---------- ollama check ----------
if command -v ollama >/dev/null 2>&1; then
    ok "Ollama detected ($(ollama --version 2>/dev/null | head -n1 | awk '{print $NF}'))"
else
    warn "Ollama is not installed. To use Enclave Code with a local model:"
    printf "    %sbrew install ollama%s\n" "$BOLD" "$RESET"
    printf "    %sollama serve &%s\n" "$BOLD" "$RESET"
    printf "    %sollama pull llama3.2%s\n" "$BOLD" "$RESET"
fi

# ---------- PATH hint ----------
if ! echo ":$PATH:" | grep -q ":$HOME/.local/bin:"; then
    warn "$HOME/.local/bin is not on your PATH. Add this to your shell rc:"
    printf "    %sexport PATH=\"\$HOME/.local/bin:\$PATH\"%s\n" "$BOLD" "$RESET"
fi

# ---------- done ----------
echo
ok "Installed. Next steps:"
printf "    %senclave init%s\n" "$BOLD" "$RESET"
printf "    %senclave models use llama3.2%s   %s(or another local model)%s\n" "$BOLD" "$RESET" "$DIM" "$RESET"
printf "    %senclave chat%s\n" "$BOLD" "$RESET"
echo
printf "%sDocs:%s https://github.com/caelusway/enclave-code\n" "$DIM" "$RESET"
