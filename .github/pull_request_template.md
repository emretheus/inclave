<!-- Read CONTRIBUTING.md first if you haven't. -->

## What
<!-- One sentence on what changed. -->

## Why
<!-- The reason — bug report, missing feature, user-facing pain. -->

## How tested
<!--
List the tests you added and any manual verification you did.
A bug fix without a regression test will be sent back.
-->

## Checklist
- [ ] Tests added or updated
- [ ] `uv run ruff check . && uv run ruff format --check .` is clean
- [ ] `uv run mypy packages shared` is clean
- [ ] `uv run pytest --cov` is clean (≥75% coverage)
- [ ] If this changes a cross-package contract (`api.py`), it has reviewers from each affected package
- [ ] If this touches the sandbox or any network call, a maintainer has been pinged
