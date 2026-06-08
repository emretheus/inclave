# InClave Desktop

A native-feeling macOS desktop app for InClave — React + TailwindCSS v4 +
shadcn/ui in a Tauri shell, driving the same privacy-first Python engine as the
CLI through a JSON-RPC sidecar.

## Architecture

```
React UI  ──Tauri invoke/events──▶  Rust shell  ──JSON-RPC over stdio──▶  inclave-bridge (Python)
(this app)                          (src-tauri)                            (packages/bridge)
                                                                                  │
                                                          reuses inclave_core / _ollama / _sandbox
                                                          and the chat_engine orchestration
```

- The frontend never talks to Python directly. One allow-listed Rust command
  (`ipc_request`) forwards to the sidecar; sidecar notifications are re-emitted
  as the `bridge://event` Tauri event.
- The sidecar opens **no socket** — only the child's stdin/stdout. The only
  network call the whole stack makes is the engine → local Ollama (127.0.0.1).
- All assets (fonts, shiki grammars/themes, icons) are bundled — zero runtime
  network fetches, so the privacy guard stays green.

## Develop

From the repo root:

```bash
pnpm install
uv sync --all-packages --all-extras
uv run python packages/bridge/scripts/export_schema.py && pnpm gen:ipc

# Run the app (spawns the sidecar via `uv run inclave-bridge`):
pnpm tauri dev

# Or develop the UI in a plain browser with a mock backend:
pnpm --filter @inclave/desktop dev
```

> Browser-only mode uses `src/lib/mock.ts`, which simulates the same streamed
> events the real bridge emits — handy for fast UI iteration without Ollama.

## Checks

```bash
pnpm --filter @inclave/desktop lint
pnpm --filter @inclave/desktop typecheck
pnpm --filter @inclave/desktop test
cd src-tauri && cargo fmt --check && cargo clippy -- -D warnings
```

## Package a .dmg

```bash
bash apps/desktop/scripts/build-sidecar.sh   # PyInstaller → src-tauri/binaries
pnpm tauri build                              # signed/notarized if secrets set
```

## Layout

```
src/
  lib/        ipc.ts (typed Tauri bridge), mock.ts, highlighter.ts, utils.ts
  stores/     zustand: chat (streaming state machine), workspace, sessions, models, system
  components/ ui/ (shadcn primitives), Titlebar, Sidebar, StatusBar, Markdown, CodeBlock, SandboxCard
  features/   chat/, models/, settings/, onboarding/, palette/
src-tauri/
  src/        sidecar.rs (supervisor), commands.rs, menu.rs, lib.rs
```
