"""Detect file paths at the start of a chat line and split off the trailing question.

UX goal (Claude Desktop-like): drag a file, then type the question on the same
line, hit Enter — the CLI should attach the file *and* send the question.

Heuristic: walk the tokens from the left. While a token resolves to an existing
file (or a glob that expands to existing files), eat it. Stop at the first
non-path token; everything from there on (rejoined with spaces) becomes the
question.

If no leading token is a path, the whole line is just chat — return None.
"""

from __future__ import annotations

import glob
import shlex
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Drop:
    paths: list[Path]
    question: str  # may be empty


def parse_drop(line: str) -> Drop | None:
    """Detect leading file paths. Return Drop(paths, question) or None.

    `paths` is non-empty when this returns a Drop. `question` may be "" if the
    line was paths-only.
    """
    stripped = line.strip()
    if not stripped:
        return None
    # Slash commands look like "/word ..." — a leading "/" followed by an
    # alphanumeric token. A real absolute path "/Users/..." has a "/" in the
    # second position, so it's distinguishable. We disambiguate by checking
    # whether the first token, taken literally, points at an existing file.
    if stripped.startswith("/"):
        first = stripped.split(maxsplit=1)[0]
        if not Path(first).is_file() and not any(ch in first for ch in "*?["):
            return None

    try:
        tokens = shlex.split(stripped, posix=True)
    except ValueError:
        return None
    if not tokens:
        return None

    paths: list[Path] = []
    rest_idx = 0
    for i, tok in enumerate(tokens):
        candidate = _strip_quotes(tok)
        expanded = Path(candidate).expanduser()
        if any(ch in candidate for ch in "*?["):
            matches = sorted(Path(p) for p in glob.glob(str(expanded)) if Path(p).is_file())
            if not matches:
                break
            paths.extend(matches)
            rest_idx = i + 1
            continue
        if expanded.is_file():
            paths.append(expanded.resolve())
            rest_idx = i + 1
            continue
        break

    if not paths:
        return None

    # Reconstruct the trailing question from the original (post-shlex) tokens.
    question = " ".join(tokens[rest_idx:]).strip()

    # Dedup paths preserving order.
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)

    return Drop(paths=unique, question=question)


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s
