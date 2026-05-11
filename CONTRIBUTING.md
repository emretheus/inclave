# Contributing to InClave

Thanks for thinking about contributing. This is a small project with a
strong privacy promise, so we keep the bar high on tests, scope, and
review. None of that is meant to be exhausting — read this once and it
should explain itself.

## Before you start

- For bug fixes that change ≤ ~30 lines, just open a PR.
- For anything bigger — new features, refactors, dependency additions,
  cross-package contract changes — **open an issue first** so we can
  agree on the shape before you spend time on it.
- If you're touching the **sandbox** or the **outbound-HTTP boundary**,
  loop in a maintainer early (see CODEOWNERS once we add it; for now,
  `@ulgacemre`).

## Getting set up

```bash
git clone https://github.com/emretheus/inclave.git
cd inclave
uv sync --all-packages --all-extras
```

Make sure Ollama is installed:

```bash
brew install ollama
ollama serve &
ollama pull llama3.2
```

## The checks CI runs (run them locally first)

```bash
uv run ruff check .             # lint
uv run ruff format --check .    # format
uv run mypy packages shared     # type-check, --strict
uv run pytest --cov             # unit tests + coverage
```

All four must pass. CI also runs two guards:

1. **No secrets** — fails if private keys or `sk-` style API tokens are
   committed.
2. **No outbound HTTP** — every URL referenced in `packages/` or
   `shared/` production code must be `127.0.0.1` or `localhost`. This
   is what backs the README's privacy promise. If you genuinely need
   to reach a non-local host, talk to a maintainer; the guard will
   block the PR otherwise.

## Pull request rules

- **Tests are required.** Bug fix? Regression test that fails before
  your patch. New feature? Tests covering the happy path and at least
  one edge case. Coverage is gated at 75 % and ratcheting up.
- **Keep PRs small.** One logical change per PR. Renames, refactors,
  and features each go in their own PR.
- **Don't reformat unrelated code.** Use `ruff format` on your changes
  only.
- **Cross-package contract changes** (anything in an `api.py`) need a
  reviewer from each affected package.
- **Don't add dependencies casually.** Especially anything that opens a
  network connection or runs at import time. Sandbox runtime deps are
  even tighter: see `packages/sandbox/runtime/README.md`.

### PR description template

Your PR description should answer three questions:

```
## What
One sentence on what changed.

## Why
The reason — bug report, missing feature, user-facing pain.

## How tested
List the tests you added and any manual verification you did.
```

## Commit messages

Follow the existing log: a Conventional-Commit-ish prefix
(`feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`), a short
subject line, and a body that explains the **why** of the change.

```
feat(cli): /save names a chat session

Autosave already wrote ~/.inclave/sessions/last.json after each turn,
but there was no way to give a session a memorable name from inside
the REPL. /save <name> writes a named copy alongside last.json.
```

No trailers, no emoji.

## Scope reminders

InClave is intentionally narrow. Out of scope without a prior
conversation:

- Hosted services, accounts, telemetry, auto-update.
- Linux / Windows ports (Linux is on the roadmap via `bubblewrap`; ask
  before starting).
- Image / voice / video input.
- Plugin or extension systems.
- Custom Seatbelt profiles per project.

If you want one of those, open an issue describing the use case and
we'll talk about whether and how to support it.

## Be decent

Attack ideas, not people. That's the whole policy.
