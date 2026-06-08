def delete_session(name: str) -> Path:
    """Delete the named session file. Returns the path that was removed.

    Raises CLIError if the session does not exist.
    """
    path = _session_path(name)
    if not path.exists():
        raise CLIError(f"session not found: {name!r}")
    path.unlink()
    return path


@dataclass
class SessionSummary:
    name: str
    saved_at: str
    model: str
    turns: int
    file_count: int


def list_sessions() -> list[SessionSummary]:
    """Return summaries, newest first. `last` always sorts to top if it exists;
    named sessions follow by saved_at descending.
    """
    root = sessions_dir()
    out: list[SessionSummary] = []
    last_entry: SessionSummary | None = None

    for p in root.glob("*.json"):
        name = p.stem
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        if not isinstance(data, dict):
            continue

        ts = data.get("saved_at", "")
        ts = ts if isinstance(ts, str) else ""

        model = data.get("model", "")
        model = model if isinstance(model, str) else ""

        msgs = data.get("messages", [])
        turns = (
            sum(1 for m in msgs if isinstance(m, dict) and m.get("role") == "assistant")
            if isinstance(msgs, list)
            else 0
        )

        fids = data.get("file_ids", [])
        file_count = len(fids) if isinstance(fids, list) else 0

        entry = SessionSummary(
            name=name,
            saved_at=ts,
            model=model,
            turns=turns,
            file_count=file_count,
        )

        if name == LAST:
            last_entry = entry
        else:
            out.append(entry)

    out.sort(key=lambda x: x.saved_at, reverse=True)

    if last_entry is not None:
        out.insert(0, last_entry)

    return out