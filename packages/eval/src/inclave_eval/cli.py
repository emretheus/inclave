"""`inclave-eval` entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .report import render_text, summarize, to_json
from .runner import FixtureModel, Model, OllamaModel, run_tasks
from .tasks import GOOD_REPLIES, load_tasks


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="inclave-eval",
        description="Run InClave accuracy and latency benchmarks.",
    )
    p.add_argument(
        "--live",
        action="store_true",
        help="run against a real Ollama model instead of recorded fixtures",
    )
    p.add_argument(
        "--model",
        default=None,
        help="model to benchmark in --live mode (defaults to the configured model)",
    )
    p.add_argument("--num-ctx", type=int, default=None, help="override options.num_ctx")
    p.add_argument("--json", type=Path, default=None, help="write full results to a JSON file")
    p.add_argument(
        "--fail-under",
        type=float,
        default=None,
        help="exit non-zero if the pass rate falls below this percentage",
    )
    return p


def _resolve_model(args: argparse.Namespace) -> tuple[Model, str]:
    if not args.live:
        return FixtureModel(GOOD_REPLIES), "fixtures"

    model = args.model
    if not model:
        # Imported here so fixture runs never need inclave_core's config layer.
        from inclave_core.config import load_config

        model = load_config().default_model
    if not model:
        raise SystemExit("no model configured — pass --model, or set default_model in config.json")
    return OllamaModel(model, num_ctx=args.num_ctx), model


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tasks = load_tasks()

    model, label = _resolve_model(args)
    results = run_tasks(tasks, model)
    summary = summarize(results, model=label, live=args.live)

    print(render_text(summary, results))

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(to_json(summary, results), indent=2))
        print(f"\nwrote {args.json}")

    if args.fail_under is not None and summary.pass_rate * 100 < args.fail_under:
        print(
            f"\npass rate {summary.pass_rate * 100:.0f}% is below "
            f"--fail-under {args.fail_under:.0f}%",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
