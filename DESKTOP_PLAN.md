# InClave Desktop — Implementation Plan

> Turning the InClave CLI into a **pixel-perfect, native-feeling macOS desktop
> application** with React + TailwindCSS + shadcn/ui + Tauri — without throwing
> away the privacy-first Python engine that already exists.

**Status:** Implemented (v1 scaffold complete; all phases landed — see §10)
**Target platform (v1):** macOS 13+ (Apple Silicon + Intel)
**Owners:** Ulgac (sandbox/IPC), Emre (frontend + Tauri shell), Ibrahim (Ollama/model UX)
**Last updated:** 2026-06-07

> **Implementation note (2026-06-07):** This plan has been built. The monorepo,
> the `inclave-bridge` sidecar, the shared `chat_engine`, the React/Tailwind/
> shadcn frontend, the Tauri Rust shell, the generated IPC contract, tests
> across all three ecosystems, and the CI + release workflows all exist in the
> repo. End-to-end verified: file attach → model writes Python → Seatbelt
> sandbox auto-runs it → grounded answer, all through the same JSON-RPC contract
> the desktop uses. Packaging (PyInstaller + notarization) is scripted and wired
> into CI but produces real `.dmg`s only when run on a signing-capable runner.

---

## 1. Goal & non-goals

### Goal

Ship a desktop app that delivers the same guarantees as the CLI — **local-only,
no telemetry, sandboxed code execution, no data leaves the machine** — wrapped
in a polished, modern, *native-feeling* macOS UI. The app must look and feel
like a first-class Mac citizen (vibrancy, traffic lights, native menus,
keyboard-driven), not an Electron-style web page in a window.

The desktop app is an **additional front-end**, not a rewrite. The Python
packages remain the single source of truth for all privileged operations
(sandbox, Ollama, workspace, sessions, config). The CLI keeps working,
unchanged.

### Non-goals (v1)

- Windows / Linux desktop builds. (Tracked under the existing CLI roadmap;
  the sandbox is macOS-only today.)
- Cloud sync, accounts, or any network call beyond `127.0.0.1:11434`.
- Rewriting the engine in Rust. Rust is the **shell + IPC broker only**.
- Replacing the CLI. Both share one engine.

---

## 2. Where we are today (codebase audit)

InClave is a **`uv` Python workspace** with four packages exposing clean,
typed, dataclass-based public APIs. These APIs are the seam we build the
desktop on — we do **not** touch the engine internals.

| Package | Path | Public surface we reuse |
|---|---|---|
| `inclave-core` | `shared/inclave_core` | `InClaveConfig`, `load_config`/`save_config`/`set_config_value`; `Session`, `save_session`/`load_session`/`list_sessions`; `FileEntry`, `add_file`/`remove_file`/`find_file`/`list_files`/`clear_workspace`; `enclave_dir`/`workspace_dir`; typed errors (`InClaveError` hierarchy); `get_logger` |
| `inclave-ollama` | `packages/ollama` | `ModelInfo`, `list_models`, `pull_model` (streams progress), `remove_model`, `set_default`/`get_default`, `generate`, `stream`, `is_model_fully_vram_compatible`, `get_total_ram_gb` |
| `inclave-sandbox` | `packages/sandbox` | `SandboxPolicy`, `ExecutionResult`, `execute_python` (Seatbelt-jailed) |
| `inclave-cli` | `packages/cli` | The REPL orchestration logic in `chat.py` — **the behavior we re-implement in the IPC layer**: code-block detection (`CODE_BLOCK_RE`, `_python_blocks_in`), the auto-run loop (`MAX_AUTORUN_TURNS`), the sandbox-observation feedback (`_format_sandbox_observation`), prompt assembly (`context.py`), drop detection (`dropdetect.py`) |

### Critical behaviors that must survive the port

These live in `packages/cli/src/inclave_cli/chat.py` and are the *real product*.
They cannot be reimplemented in JS — they must run server-side in Python:

1. **Streaming chat** over `ollama.chat(..., stream=True)` (`_stream_chat`).
2. **Auto-run loop**: detect a `python` fenced block in the assistant's reply →
   run it in the sandbox → feed stdout/stderr back as a synthetic user turn →
   model writes a grounded summary. Capped at `MAX_AUTORUN_TURNS = 3`.
3. **Sandboxed execution**: temp workdir, copy attached files in, apply
   `SandboxPolicy` (CPU/mem/wall-clock), tear down (`_execute_in_sandbox`).
4. **Prompt assembly**: `SYSTEM_PROMPT` + `<<<FILE>>>` blocks + caps
   (5 files / 200 KB total / 100 KB per file) (`context.py`).
5. **Autosave after every turn** (`_autosave` → `save_session(..., LAST)`).
6. **Drag-and-drop file attach** (`dropdetect.parse_drop`) — natively richer in
   a desktop window than in a terminal.

### Hard constraints from the existing repo

- **Privacy guard** (`.github/workflows/ci.yml`): no non-localhost URLs in
  production code. The desktop frontend must obey this too — no CDN fonts, no
  analytics, no remote anything. All assets bundled.
- **Tests mandatory on every PR**; CI blocks merges without them
  (coverage gate currently `COV_MIN=75`, sandbox targeted at ≥90%).
- **No `Co-Authored-By` trailers** in commits.
- `uv` workspace conventions: `pyproject.toml` per package, strict `mypy`,
  `ruff` lint+format.

---

## 3. Architecture decision: Tauri + Python sidecar

### The core decision

The privileged work (spawning `sandbox-exec`, talking to Ollama, reading
`~/.inclave`) **must stay in Python** — it's already written, tested, and is
the thing reviewers trust for the privacy promise. So the desktop app is:

```
┌─────────────────────────────────────────────────────────────┐
│  Tauri app window (native macOS, WKWebView)                   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  React 19 + TypeScript + Tailwind v4 + shadcn/ui     │    │
│  │  (the pixel-perfect UI — chat, files, models, prefs) │    │
│  └───────────────────────┬─────────────────────────────┘    │
│                          │ Tauri IPC (invoke + events)        │
│  ┌───────────────────────▼─────────────────────────────┐    │
│  │  Rust core (apps/desktop/src-tauri)                  │    │
│  │  - window chrome, native menu, vibrancy, deep links  │    │
│  │  - spawns + supervises the Python sidecar            │    │
│  │  - proxies IPC <-> sidecar over local stdio/loopback │    │
│  └───────────────────────┬─────────────────────────────┘    │
│                          │ JSON-RPC over stdio (127.0.0.1)    │
│  ┌───────────────────────▼─────────────────────────────┐    │
│  │  Python sidecar = inclave-bridge (NEW package)       │    │
│  │  Thin async server. Imports inclave_core /           │    │
│  │  inclave_ollama / inclave_sandbox and re-uses        │    │
│  │  chat.py orchestration. Emits stream/run events.     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
              All of the above runs locally. Only the
              sidecar ever opens a socket — to 127.0.0.1:11434.
```

### Why a Python sidecar and not "rewrite the engine in Rust"

- The sandbox executor, the auto-run loop, prompt assembly, file parsing
  (`pandas`/`openpyxl`/`pypdf`), and Ollama streaming are **already done and
  tested in Python**. Re-implementing them in Rust would duplicate the entire
  product surface and double the privacy-review burden.
- One engine, two front-ends (CLI + desktop) = no behavior drift. A bug fixed
  in `chat.py` benefits both.
- Tauri sidecars are a first-class, documented pattern.

### Why Tauri and not Electron

- **Bundle size:** ~10–15 MB vs Electron's ~120 MB+. Matches the lean,
  no-bloat ethos.
- **Native macOS feel:** WKWebView + Rust gives us vibrancy, native menus,
  traffic-light positioning, and OS-level secure storage for free.
- **Security posture:** explicit allow-list IPC, no full Node runtime in the
  renderer — aligns with the privacy guarantee.
- **No outbound network by default** — fits the CI privacy guard cleanly.

### IPC transport

- **Sidecar protocol:** newline-delimited JSON-RPC 2.0 over the sidecar's
  stdio (Tauri's `Command::new_sidecar` gives us stdout/stdin pipes and
  lifecycle). Streaming responses (chat tokens, pull progress, sandbox output)
  are sent as JSON-RPC *notifications*; Rust re-emits them to the webview as
  Tauri events.
- **Frontend never talks to Python directly.** It calls Rust `#[tauri::command]`
  wrappers, which forward to the sidecar. This keeps a single, auditable
  trust boundary and lets us lock down the IPC allow-list.
- **Why stdio over a TCP port:** no listening socket at all on the user's
  machine → strictly better privacy story and nothing for the CI guard or a
  reviewer to worry about. (A loopback HTTP server is the documented fallback
  if a streaming-backpressure issue forces it.)

---

## 4. Monorepo layout (everything in this repo)

We extend the existing `uv` workspace and add a `pnpm` workspace alongside it.
One repo, two language toolchains, shared root.

```
inclave/
├── README.md
├── DESKTOP_PLAN.md                  ← this file
├── pyproject.toml                   # uv workspace root (extended: + bridge member)
├── uv.lock
├── package.json                     # NEW: pnpm workspace root (JS toolchain)
├── pnpm-workspace.yaml              # NEW
├── turbo.json                       # NEW: task orchestration (build/lint/test)
│
├── shared/
│   └── inclave_core/                # unchanged
│
├── packages/                        # Python engine (unchanged)
│   ├── cli/
│   ├── ollama/
│   ├── sandbox/
│   │
│   └── bridge/                      # NEW Python pkg: inclave-bridge
│       ├── pyproject.toml           #   depends on core/ollama/sandbox + cli orchestration
│       ├── src/inclave_bridge/
│       │   ├── __init__.py
│       │   ├── server.py            # JSON-RPC loop over stdio
│       │   ├── protocol.py          # request/response/notification dataclasses + JSON schema
│       │   ├── handlers/
│       │   │   ├── chat.py          # wraps chat.py orchestration; streams tokens + run events
│       │   │   ├── models.py        # list/pull/remove/set-default (+ VRAM check)
│       │   │   ├── files.py         # add/remove/list/clear workspace
│       │   │   ├── sessions.py      # list/load/save/delete
│       │   │   └── config.py        # get/set config
│       │   ├── events.py            # typed event emitters (token, run-start, run-output…)
│       │   └── py.typed
│       └── tests/
│           ├── test_protocol.py
│           ├── test_chat_handler.py
│           ├── test_models_handler.py
│           └── test_server_smoke.py
│
├── apps/                            # NEW: JS/desktop side
│   └── desktop/
│       ├── package.json
│       ├── index.html
│       ├── vite.config.ts
│       ├── tailwind.config.ts
│       ├── components.json          # shadcn/ui config
│       ├── tsconfig.json
│       ├── src/                     # React app (see §6)
│       │   ├── main.tsx
│       │   ├── App.tsx
│       │   ├── routes/
│       │   ├── features/            # chat/, files/, models/, sessions/, settings/, onboarding/
│       │   ├── components/ui/       # shadcn primitives
│       │   ├── components/          # app-level composites
│       │   ├── lib/
│       │   │   ├── ipc.ts           # typed wrapper over Tauri invoke + event subscriptions
│       │   │   ├── types.ts         # generated from Python protocol (see §7.3)
│       │   │   └── utils.ts
│       │   ├── stores/              # Zustand stores (chat, workspace, models, ui)
│       │   ├── hooks/
│       │   └── styles/globals.css
│       ├── src-tauri/               # Rust shell
│       │   ├── Cargo.toml
│       │   ├── tauri.conf.json
│       │   ├── build.rs
│       │   ├── binaries/            # bundled python sidecar (built by PyOxidizer/PyInstaller)
│       │   ├── icons/
│       │   └── src/
│       │       ├── main.rs
│       │       ├── sidecar.rs       # spawn/supervise sidecar, pipe JSON-RPC
│       │       ├── commands.rs      # #[tauri::command] wrappers → sidecar
│       │       ├── menu.rs          # native macOS menu
│       │       └── events.rs        # forward sidecar notifications → webview
│       └── tests/                   # vitest + playwright (see §11)
│
├── packages-js/                     # NEW (optional): shared JS libs
│   └── ipc-contract/                # generated TS types + zod schemas from protocol.py
│
└── .github/workflows/
    ├── ci.yml                       # extended: + desktop lint/typecheck/test job
    └── release-desktop.yml          # NEW: signed + notarized .dmg build
```

### Tooling choices

| Concern | Choice | Rationale |
|---|---|---|
| JS package manager | **pnpm** | Fast, strict, great workspace support; small disk footprint |
| Task runner | **Turborepo** | Cache + orchestrate `build/lint/test` across JS packages |
| Bundler | **Vite** | Tauri's default; fast HMR |
| Framework | **React 19 + TypeScript (strict)** | Requested; mature shadcn support |
| Styling | **Tailwind CSS v4** | Requested; CSS-first config, design tokens |
| Components | **shadcn/ui** (Radix primitives) | Requested; accessible, owned-in-repo, themeable |
| State | **Zustand** + **TanStack Query** | Light global state + cache/async for IPC reads |
| Animation | **Framer Motion** | Streaming text, view transitions, micro-interactions |
| Markdown | **react-markdown** + **shiki** | Render assistant replies; syntax-highlight code blocks offline |
| Shell | **Tauri 2.x (Rust)** | Native macOS, small bundle, secure IPC |
| Sidecar package | **PyInstaller** (onedir) | Bundle Python engine into the app; no system Python needed |

> **Privacy note for the frontend:** shiki grammars/themes, fonts (e.g.
> Inter / SF fallback), and all icons are **vendored and bundled** — zero
> network fetches at runtime, so the CI privacy guard stays green.

---

## 5. The IPC contract (the heart of the integration)

A single typed contract drives Rust, Python, and TypeScript. Defined once in
`packages/bridge/src/inclave_bridge/protocol.py` as dataclasses, with a
JSON-Schema export that **generates** the TypeScript types + zod validators
(see §7.3). This guarantees the three languages never drift.

### 5.1 Request methods (frontend → sidecar)

| Method | Params | Returns | Notes |
|---|---|---|---|
| `system.status` | – | `{ ollama_running, default_model, ram_gb, sandbox_ok }` | Powers the status bar + onboarding gate |
| `chat.send` | `{ session_id, text, file_ids[] }` | stream (see events) | Runs full orchestration incl. auto-run loop |
| `chat.cancel` | `{ session_id }` | `ok` | Interrupts stream / sandbox run |
| `chat.run_last` | `{ session_id }` | stream | `/run` escape hatch |
| `models.list` | – | `ModelInfo[]` (+ `vram_ok`) | |
| `models.pull` | `{ name }` | stream (progress events) | |
| `models.remove` | `{ name }` | `ok` | |
| `models.set_default` | `{ name }` | `ok` | |
| `files.add` | `{ paths[] }` | `FileEntry[]` | Drag-drop or file picker |
| `files.list` | `{ scope: "workspace"\|"session", session_id? }` | `FileEntry[]` | |
| `files.remove` | `{ ref }` | `ok` | |
| `files.clear` | – | `{ removed: n }` | |
| `sessions.list` | – | `{ name, saved_at, model, n_turns }[]` | |
| `sessions.load` | `{ name }` | `Session` | |
| `sessions.save` | `{ name, session }` | `ok` | |
| `sessions.delete` | `{ name }` | `ok` | NEW capability (CLI has none; add to core) |
| `config.get` | – | `InClaveConfig` | |
| `config.set` | `{ key, value }` | `InClaveConfig` | Reuses `set_config_value` |
| `ollama.ensure_running` | – | stream (startup progress) | Mirrors onboarding |

### 5.2 Notification events (sidecar → frontend, streamed)

| Event | Payload | Emitted during |
|---|---|---|
| `chat.token` | `{ session_id, delta }` | streaming assistant reply |
| `chat.message_done` | `{ session_id, role, content }` | full turn committed |
| `chat.run_start` | `{ session_id, code }` | a python block is about to run |
| `chat.run_output` | `{ session_id, stdout, stderr, exit_code, duration_ms, timed_out }` | sandbox finished |
| `chat.turn_done` | `{ session_id, n_turns }` | whole turn (incl. auto-run loop) complete |
| `models.pull_progress` | `{ name, status, completed, total }` | model download |
| `system.ollama_state` | `{ running }` | daemon up/down transitions |
| `error` | `{ code, message, where }` | maps `InClaveError` subclasses |

### 5.3 Error model

The Python `InClaveError` hierarchy (`OllamaUnavailableError`, `SandboxError`,
`ConfigError`, `CLIError`) maps to stable string error codes in the protocol so
the UI can render specific, friendly recoveries (e.g. "Ollama isn't running —
[Start it]" for `ollama_unavailable`).

---

## 6. UI/UX design — pixel-perfect macOS

### 6.1 Information architecture

A **two/three-pane macOS layout** (think Mail / Things 3 / Linear-for-desktop):

```
┌──────────────────────────────────────────────────────────────────────┐
│ ●●●   InClave                                          [model ▾] [⚙]   │  ← custom titlebar (vibrancy, draggable)
├───────────────┬──────────────────────────────────────────────────────┤
│  SIDEBAR      │  CHAT (main)                                           │
│               │                                                        │
│  ＋ New chat  │   ┌──────────────────────────────────────────────┐    │
│               │   │ user: print total mrr growth                  │    │
│  CHATS        │   │   ▸ mrr_2026.csv (chip)                       │    │
│  • Q1 review  │   ├──────────────────────────────────────────────┤    │
│  • mrr growth │   │ assistant: …streaming…                        │    │
│  • (last)     │   │   ```python  [Run ▸] [Copy]                   │    │
│               │   │   import pandas …                             │    │
│  WORKSPACE    │   │   ```                                         │    │
│  📄 q1.pdf    │   │   ╭ stdout ─────────╮  ran · exit 0 · 1.2s    │    │
│  📊 mrr.csv   │   │   │ 96.06%          │                         │    │
│  ＋ Add files │   │   ╰─────────────────╯                         │    │
│               │   └──────────────────────────────────────────────┘    │
│               │   ┌──────────────────────────────────────────────┐    │
│               │   │ Drop files or type a message…       [⏎ Send]  │    │  ← composer (drag target)
│               │   └──────────────────────────────────────────────┘    │
├───────────────┴──────────────────────────────────────────────────────┤
│ ● Ollama: running   qwen2.5-coder:7b   workspace: 2 files   ⌘K        │  ← status bar
└──────────────────────────────────────────────────────────────────────┘
```

- **Left sidebar:** sessions list (autosaved `last` pinned to top, named below),
  collapsible **Workspace files** section with kind icons + size, "Add files".
- **Main pane:** the chat transcript. This is where the "pixel-perfect" effort
  concentrates (see §6.4).
- **Status bar:** mirrors the CLI banner — Ollama state, active model, file
  count, ⌘K hint. Live, driven by `system.ollama_state` events.
- **Command palette (⌘K):** switch model, new chat, add files, jump to session,
  open settings — Linear-style, keyboard-first.

### 6.2 Native macOS chrome

- **Custom titlebar** with `titleBarStyle: Overlay` + transparent traffic
  lights inset; window is draggable via the titlebar region.
- **Vibrancy / translucency** behind the sidebar (`NSVisualEffectView` via
  Tauri's `macos-private-api` / `window-vibrancy`).
- **Native menu bar** (File / Edit / Chat / Model / View / Window / Help) with
  real shortcuts: ⌘N new chat, ⌘O add files, ⌘⏎ run last, ⌘K palette,
  ⌘, settings.
- **Dark mode follows the system** by default, with manual override in settings.
- Respects **reduce-motion** and **reduce-transparency** accessibility settings.

### 6.3 Design system & tokens

- **Tailwind v4 CSS-first tokens** in `globals.css`: a neutral, calm palette
  (privacy/trust = restrained, not flashy), one accent (a deep teal/indigo),
  semantic tokens for `bg/surface/border/muted/accent/destructive` mapped to
  light+dark.
- **Typography:** SF Pro (system) for UI; a mono (e.g. SF Mono / JetBrains
  Mono, bundled) for code + sandbox output.
- **Radius / spacing / shadow scale** standardized via shadcn theme.
- shadcn components we'll pull in: `button`, `input`, `textarea`, `dialog`,
  `dropdown-menu`, `command`, `tooltip`, `scroll-area`, `tabs`, `badge`,
  `progress`, `switch`, `select`, `sonner` (toasts), `skeleton`, `separator`,
  `resizable` (panes).

### 6.4 The hero surface — chat transcript

This is what makes it feel premium:

- **Streaming text** rendered token-by-token with a soft caret; Framer Motion
  for entrance. Markdown via react-markdown.
- **Code blocks**: shiki syntax highlighting (offline grammars), a header bar
  with language label, **Copy**, and **Run ▸** (manual re-run). When auto-run
  fires, the block shows a subtle "running…" shimmer.
- **Sandbox output card**: the CLI's `╭ stdout ╮` panel reimagined — a
  collapsible card with stdout/stderr tabs, exit code badge (green/red),
  duration, and a "timed out" state. This directly mirrors
  `ui.render_sandbox_output`.
- **File chips** on user messages show attached files with kind icon; click to
  preview.
- **Empty state / onboarding** (see §6.5).

### 6.5 Onboarding & empty states (ports `onboarding.py`)

First launch walks the user through the exact CLI flow, but visually:

1. **Welcome** — privacy promise, "everything stays on your Mac."
2. **Ollama check** — if not running, a button to start it (calls
   `ollama.ensure_running`); if not installed, copy-paste `brew install ollama`.
3. **Pick a model** — curated cards (`llama3.2`, `llama3.1:8b`,
   `qwen2.5-coder:7b`) with size + a **VRAM compatibility badge** computed from
   `is_model_fully_vram_compatible` + `get_total_ram_gb` (green "fits in
   memory" / amber "will swap, slow"). Pull with a live progress bar
   (`models.pull` stream).
4. **Drop your first file** — animated drag target → straight into chat.

Empty chat state: a friendly prompt with example questions and a big drop zone.

### 6.6 Drag-and-drop

Tauri's native file-drop events give us real paths (richer than the CLI's
`dropdetect`). Dropping anywhere on the window highlights the composer; on drop
we call `files.add` then attach to the active session. Mirrors the CLI's
"drop a file, ask a question" affordance.

---

## 7. Cross-language type safety

### 7.1 Single source of truth

`protocol.py` (dataclasses) is canonical. It already aligns with the engine's
dataclasses (`ModelInfo`, `FileEntry`, `Session`, `InClaveConfig`,
`ExecutionResult`).

### 7.2 Schema export

A small script `packages/bridge/scripts/export_schema.py` dumps the protocol to
`packages-js/ipc-contract/schema.json` (JSON Schema).

### 7.3 TS generation

`pnpm gen:ipc` runs `json-schema-to-zod` (or `quicktype`) → produces
`packages-js/ipc-contract/index.ts` with **zod schemas + inferred TS types**.
`apps/desktop/src/lib/types.ts` re-exports them. A CI check fails if the
committed generated file is stale (regenerate-and-diff), so Python and TS can
never drift.

### 7.4 Runtime validation

`lib/ipc.ts` validates every sidecar payload with the generated zod schema
before it reaches React — a malformed message is surfaced as a typed error, not
a silent crash.

---

## 8. Security & privacy (must-hold invariants)

The desktop app inherits and must not weaken the CLI's promises:

1. **No outbound network** except the sidecar → `127.0.0.1:11434`. The webview
   has **no** network capability needed; CSP locks it to `self`. Tauri's
   allow-list disables shell/http/fs plugins we don't use.
2. **Sandbox unchanged.** Code execution still goes through
   `inclave_sandbox.execute_python` (Seatbelt, no network, rlimits). The
   desktop never spawns code itself — only the audited engine does.
3. **IPC allow-list:** only the explicit `#[tauri::command]` set is exposed; the
   frontend cannot run arbitrary Rust or Python.
4. **CSP:** `default-src 'self'; connect-src 'self' ipc:; img-src 'self' data:;`
   — no remote origins. All fonts/grammars/themes bundled.
5. **No telemetry, no auto-update phone-home.** Updates (if any) are
   user-initiated downloads of a signed `.dmg`.
6. **Extend the CI privacy guard** to also grep `apps/desktop/src/**` and the
   Rust shell for non-localhost URLs.
7. **Workspace data** still lives only under `~/.inclave/`. The app reads/writes
   nothing else outside the user-chosen drop files + the sandbox temp dir.
8. **Code signing + notarization** for distribution (Developer ID, hardened
   runtime, `com.apple.security.*` entitlements minimal).

---

## 9. Build, packaging & distribution

### 9.1 Bundling the Python sidecar

- Build the engine into a self-contained binary with **PyInstaller (onedir)**,
  including `pandas`/`numpy`/`openpyxl`/`pypdf`/`matplotlib` and the sandbox
  runtime venv layout the executor expects.
- Output goes to `apps/desktop/src-tauri/binaries/inclave-bridge-<target>`.
- Tauri's `externalBin` / `Command::new_sidecar` bundles + spawns it.
- The Seatbelt profile (`packages/sandbox/profiles/default.sb`) and the sandbox
  runtime Python must be packaged so paths resolve inside the app bundle
  (audit `runtime.py`'s `python_install_root`/`runtime_python` for bundle-aware
  paths — this is a known integration risk, see §13).

### 9.2 Universal binary

Build for `aarch64-apple-darwin` and `x86_64-apple-darwin`, `lipo` into a
universal `.app`. The Python sidecar likewise built per-arch and merged (or
ship arch-specific DMGs to start).

### 9.3 Release pipeline

`.github/workflows/release-desktop.yml` on tag:

1. `uv sync` + PyInstaller build the sidecar (macos runner).
2. `pnpm install` + `pnpm --filter desktop tauri build`.
3. **Codesign** with Developer ID + **notarize** (notarytool) + staple.
4. Produce `.dmg`, attach to GitHub Release.

---

## 10. Implementation phases & milestones

Each phase is independently shippable and **lands with tests** (per the team's
testing discipline — CI blocks merges without them).

### Phase 0 — Monorepo foundations (1 week)
- Add `pnpm-workspace.yaml`, root `package.json`, `turbo.json`.
- Scaffold `apps/desktop` (Vite + React + TS + Tailwind v4 + shadcn init).
- Scaffold `src-tauri` (Tauri 2, opens a blank window, native titlebar).
- Extend CI: a `desktop` job (`pnpm lint`, `tsc --noEmit`, `vitest`,
  `cargo clippy`, `cargo test`). Privacy guard extended to JS/Rust.
- **Deliverable:** empty signed window launches via `pnpm tauri dev`.

### Phase 1 — `inclave-bridge` sidecar + IPC contract (1.5 weeks)
- New `packages/bridge` Python package; `protocol.py` + JSON-RPC `server.py`.
- Handlers for `config`, `files`, `sessions`, `models` (non-streaming first).
- Schema export + TS generation pipeline (`pnpm gen:ipc`).
- Rust: spawn/supervise sidecar, `commands.rs` wrappers, event forwarding.
- **Tests:** `pytest` on protocol + handlers; a Rust integration test that
  boots the sidecar and round-trips `config.get`.
- **Deliverable:** React can read config/models/files/sessions over typed IPC.

### Phase 2 — Streaming chat + auto-run loop (2 weeks) ← the core
- `handlers/chat.py` reuses `chat.py` orchestration: stream tokens, detect
  python blocks, run in sandbox, feed observation back, summarize. Emit the
  `chat.*` events.
- React chat surface: transcript, streaming render, code blocks (shiki),
  sandbox output card, composer, cancel.
- Autosave-after-turn wired through `sessions.save(LAST)`.
- **Tests:** chat handler unit tests (mock Ollama, real sandbox where feasible
  with markers); frontend component tests for streaming + run card.
- **Deliverable:** the README demo (CSV → python → grounded answer) works
  end-to-end in the window.

### Phase 3 — Files, sessions, models UX (1.5 weeks)
- Drag-and-drop attach (native Tauri file-drop); file chips + preview.
- Sessions sidebar (load/save/rename/delete — add `delete_session` to core).
- Models manager: list, pull with progress, remove, set default, VRAM badge.
- **Tests:** stores + interactions; sidecar handlers.
- **Deliverable:** full feature parity with the CLI's slash commands, via UI.

### Phase 4 — Onboarding, command palette, polish (1.5 weeks)
- First-run onboarding flow (ports `onboarding.py`).
- ⌘K command palette; native menu + all shortcuts.
- Empty states, toasts, error recoveries mapped from `InClaveError` codes.
- Animation pass (Framer Motion), reduce-motion/transparency support.
- Accessibility audit (focus order, ARIA, contrast).
- **Deliverable:** feels finished and native.

### Phase 5 — Packaging, signing, release (1 week)
- PyInstaller sidecar bundling; sandbox-runtime path fixes for app bundle.
- Universal binary; codesign + notarize; `.dmg`.
- `release-desktop.yml`; smoke-test the signed build on a clean Mac.
- **Deliverable:** downloadable, notarized InClave.app.

> **Rough total:** ~8–9 weeks of focused work, parallelizable across the
> 3-person team (Ulgac: bridge/sandbox-bundling; Emre: Tauri shell + frontend;
> Ibrahim: models/onboarding UX + Ollama integration).

---

## 11. Testing strategy

Tests are mandatory on every PR (CI gate). Per layer:

| Layer | Tooling | What we test |
|---|---|---|
| Python bridge | `pytest` (+ existing markers) | protocol (de)serialization, each handler, the chat orchestration reuse, error mapping |
| Sandbox path in bundle | `pytest` integration marker | `execute_python` resolves runtime inside the app bundle layout |
| Rust shell | `cargo test` + `cargo clippy` | sidecar spawn/supervise, IPC round-trip, command allow-list |
| TS contract | `vitest` | generated zod schemas validate real payloads; stale-schema CI check |
| Frontend units | `vitest` + Testing Library | stores, hooks, chat rendering, run card, file chips |
| E2E | Playwright (via `tauri-driver` / WebDriver) | onboarding, send-message-with-file → sandbox output, model pull |
| Privacy guard | grep job (extended) | no non-localhost URLs in JS/Rust/Python prod code |

Coverage gates: keep Python ≥75% (sandbox ≥90%); add a frontend coverage gate
(start ~70%, ratchet up).

---

## 12. Changes required to existing packages (minimal, additive)

The engine stays stable. We add only:

1. **`delete_session(name)`** to `inclave_core.sessions` (UI needs delete; CLI
   never had it). Small, tested, additive.
2. **Bundle-aware path resolution** in `inclave_sandbox.runtime` — make
   `python_install_root()` / `runtime_python()` resolve correctly when running
   inside a PyInstaller/Tauri app bundle (env var or relative-to-executable
   fallback). This is the single riskiest engine touch; gate behind tests.
3. Optionally expose the chat orchestration from `chat.py` as a reusable
   **generator/coroutine** (decouple from `rich.Console`) so the bridge can
   consume it without the terminal UI. Cleanest path: extract the loop into a
   `chat_engine.py` that yields events; `chat.py` (CLI) and the bridge both
   consume it. **No behavior change** — pure refactor with the existing
   `test_chat.py` as the safety net.

These are scoped as separate, reviewable PRs (sandbox change loops in a
maintainer per CONTRIBUTING).

---

## 13. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Sandbox runtime paths break inside the app bundle | High — code exec is the product | Phase 5 dedicated path-resolution work + integration test on the signed build; keep the env-var override escape hatch |
| PyInstaller + pandas/numpy/matplotlib bloat / hidden-import breakage | Medium | onedir mode, explicit hidden-imports, smoke-test imports in CI; measure bundle size budget |
| Streaming backpressure over stdio JSON-RPC | Medium | chunked notifications + flush discipline; loopback-HTTP fallback documented |
| Tauri 2 + macOS notarization friction | Medium | Do signing in Phase 0 spike (blank window) so it's solved early, not at the end |
| Python/TS type drift | Medium | Generated contract + stale-schema CI check (§7.3) |
| Engine refactor regresses CLI | Medium | Pure-refactor approach with `test_chat.py` as guard; behavior-locked |
| Reduced privacy posture vs CLI | High (trust) | CSP + IPC allow-list + extended privacy guard; security review PR before release |

---

## 14. Open questions (for the team)

1. **Sidecar bundling:** PyInstaller (simplest, proven) vs. PyOxidizer
   (single-file, leaner) — spike both in Phase 1?
2. **Engine refactor depth:** extract `chat_engine.py` now (cleaner) vs. have
   the bridge call into `chat.py` with a fake Console adapter (faster, hackier)?
3. **Distribution:** notarized `.dmg` only, or also Homebrew Cask?
4. **Multi-window / multi-workspace:** the engine assumes a single `default`
   workspace today — do we surface multi-workspace in the desktop, or defer?
5. **Versioning:** does the desktop app version independently or lock-step with
   the CLI / engine?

---

## 15. Definition of done (v1)

- Launches as a signed, notarized macOS `.app` / `.dmg`, no system Python
  required.
- Reproduces the README demo end-to-end: drop a CSV, ask a question, watch the
  model write python, see it auto-run in the sandbox, get a grounded answer.
- Feature parity with the CLI's slash commands via UI (files, models,
  sessions, config, run-last, setup/onboarding).
- Zero outbound network beyond `127.0.0.1:11434`; CI privacy guard green across
  Python, Rust, and JS.
- Tests on every layer; CI blocks merges without them.
- Looks and feels native on macOS (vibrancy, native menu, ⌘K, dark mode,
  reduce-motion).
```

