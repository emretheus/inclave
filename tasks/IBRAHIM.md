# Tasks — Ibrahim (Ollama Integration & Model Management)

**Package:** `packages/ollama` — `enclave_ollama`
**Goal:** Wrap a local Ollama install behind a clean, typed Python API. Make model selection, pulling, switching, and prompting feel boring and reliable.

> Read `PROJECT_PLAN.md` first. The frozen API contract you must implement is in §5.2.

---

## Why this matters

You own the LLM brain of the product. If your wrapper is flaky, slow to stream, or has confusing model semantics, the whole CLI feels broken even though it isn't. The contract you expose is what Emre's CLI calls on every keystroke during a chat session — keep it tight and predictable.

---

## Scope

You own:
- `packages/ollama/src/enclave_ollama/` — implementation
- `packages/ollama/tests/` — unit + integration
- The decision of how to talk to Ollama (HTTP REST vs `ollama` Python package)
- The `OllamaError` and `OllamaUnavailableError` exception classes (subclasses of `enclave_core.errors.EnclaveError`)
- A `requires_ollama` precondition decorator (or equivalent) that the CLI applies to commands that need a live Ollama
- Default model selection persistence (delegated to `enclave_core.Config`, but you read/write through it)

You do NOT own:
- Where output is rendered (Emre)
- Conversation history / multi-turn state (Emre — your `generate` and `stream` are stateless)
- Code execution (Ulgac)

---

## Deliverables by Milestone

### M0 — Scaffolding
- [ ] `packages/ollama/pyproject.toml` declaring `enclave_ollama`, deps on `ollama` Python client.
- [ ] Stub `api.py` exporting types and functions in PROJECT_PLAN §5.2 (raise `NotImplementedError`).
- [ ] `OllamaError(EnclaveError)` and `OllamaUnavailableError(OllamaError)` defined in `enclave_ollama/errors.py` and re-exported.
- [ ] One smoke test importing the package.

### M1 — Walking skeleton
- [ ] `list_models()` returns real models from a running local Ollama instance.
- [ ] `generate(prompt, model=...)` returns the full response (non-streaming first).
- [ ] `get_default()` / `set_default()` round-trip through `enclave_core.Config`.
- [ ] If Ollama is unreachable, raise `OllamaUnavailableError` with a clear message (e.g. `"Ollama not running. Start it with: ollama serve"`) — never let raw `httpx`/`requests` exceptions leak. The CLI catches and prints the message; you do not print anything yourself.
- [ ] `requires_ollama` precondition (decorator or context manager) that runs the health check once per CLI invocation and raises `OllamaUnavailableError` early. Avoids latency on every call.
- [ ] Tests with Ollama mocked (use `respx` or a fake server fixture).

### M2 — Streaming + model lifecycle
- [ ] `stream(prompt, model=...)` yields chunks as they arrive.
- [ ] `pull_model(name)` returns an iterator of human-readable progress lines (`"pulling manifest"`, `"downloading: 234MB / 4.7GB"`, etc.).
- [ ] `remove_model(name)` deletes a local model.
- [ ] Handle: model doesn't exist locally, model name typo, pull interrupted, disk full.
- [ ] Unit tests for each error mode.
- [ ] One integration test that requires Ollama to be running locally — gated behind `pytest -m integration` so it's only run on machines that have Ollama.

### M3 — Polish
- [ ] `ModelInfo.parameter_count` parsed from the model manifest (Ollama exposes this).
- [ ] `system` prompt parameter on `generate` / `stream` — Emre will use this to inject file context. The system prompt content is owned by Emre (lives in `enclave_cli/prompts.py`); you only forward it to Ollama unchanged.
- [ ] Sensible timeouts on every call (configurable via `enclave_core.Config`).
- [ ] Cancellable streams: the iterator returned by `stream(...)` must close cleanly when the consumer stops iterating (so Emre's `Ctrl+C` cancel works without leaking connections).
- [ ] Coverage ≥ 80%.
- [ ] README in `packages/ollama/README.md` documenting: how to install Ollama, expected version, supported models tested.

---

## Implementation notes

- Use the official `ollama` Python package — don't roll your own HTTP client unless it gives you something the lib doesn't.
- Keep the API **stateless**. No singletons, no module-level config caches. The CLI passes `model=` on every call. (`get_default()` is a config-layer concern, not in-memory state.)
- For streaming, prefer `Iterator[str]` over `AsyncIterator` for v0.1 — keeps the CLI simple. We can add async later.
- Detect Ollama availability with a fast health-check call (`/api/tags` is cheap). Cache the result for the duration of one CLI invocation, not longer.
- `pull_model` progress: don't try to parse Ollama's bytes-per-second field — just yield the raw status messages it sends. UX formatting is Emre's problem.

---

## Testing rules (non-negotiable)

- Every public function has unit tests with the HTTP layer mocked.
- One integration test per public function, marked with `@pytest.mark.integration`, runs against a real local Ollama. CI optionally runs these on a self-hosted runner — for now they're best-effort locally.
- Test the failure modes explicitly: connection refused, 404 model, 500 server, partial stream cut.
- Every PR adds tests. CI blocks otherwise.

---

## Interfaces with other members

- **Emre (CLI):** your only consumer. Stay close to him on streaming UX — the difference between "feels fast" and "feels broken" is whether the first token shows up in < 200ms.
- **Ulgac (sandbox):** no direct dependency.

---

## What "done for v0.1" looks like

```python
import enclave_ollama as oll

oll.set_default("llama3.2")
for chunk in oll.stream("summarize the attached spreadsheet", system=file_context):
    print(chunk, end="", flush=True)
```

…works reliably, streams cleanly, and never leaks an HTTP exception to the caller.
