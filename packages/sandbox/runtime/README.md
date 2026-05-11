# sandbox runtime

Frozen Python runtime bundled into the `inclave-sandbox` jail. The Seatbelt
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

Adding to the runtime is a deliberate, two-place change in one PR:

1. Add the dep here in `pyproject.toml`, run `uv lock`, commit `uv.lock`.
2. Update the system prompt in `packages/cli/src/inclave_cli/context.py`
   (`SYSTEM_PROMPT`) so the model knows the new import is available.

Without both, model-generated code that uses the new lib will silently
fail to import.

## Why pinned to Python <3.14?

Some scientific-stack wheels (matplotlib, numpy) lag behind the latest CPython
release. Pinning here prevents the runtime build from picking an interpreter
without prebuilt wheels and falling back to slow source builds.
