# sandbox runtime

Frozen Python runtime bundled into the `enclave-sandbox` jail. The Seatbelt
profile permits read+exec of this directory's `.venv/`, so any library installed
here is available to model-generated code at runtime.

This is **not** a workspace member. It's a standalone uv project with its own
lock file so the runtime is reproducible across machines.

## Build

```bash
cd packages/sandbox/runtime
uv sync
```

That creates `.venv/` (gitignored) containing the locked deps. The sandbox
executor finds the interpreter at `runtime/.venv/bin/python3` and exits with
a clear "Run: cd ... && uv sync" error if it's missing.

## Adding a library

Adding to the runtime is a deliberate, three-place change in one PR:

1. Add the dep here in `pyproject.toml`, run `uv lock`, commit `uv.lock`.
2. Update PROJECT_PLAN.md §13.1 (the bundled-libs table).
3. Update the system prompt in `packages/cli/src/enclave_cli/prompts.py` so
   the model knows the new import is available.

Without all three, model-generated code that uses the new lib will silently
fail to import.

## Why pinned to Python <3.14?

Some scientific-stack wheels (matplotlib, numpy) lag behind the latest CPython
release. Pinning here prevents the runtime build from picking an interpreter
without prebuilt wheels and falling back to slow source builds.
