"""In-memory live-session store for the bridge.

A desktop session_id maps to a running conversation (the same `messages` list
shape the engine mutates) plus its attached workspace files. We autosave to disk
under the session_id name after every turn, mirroring the CLI's autosave.

`last` stays special: the most recent live session is also mirrored to `last`
so `chat --resume` from the CLI keeps working.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from inclave_core import (
    LAST,
    FileEntry,
    Session,
    find_file,
    load_session,
    save_session,
)


@dataclass
class LiveSession:
    session_id: str
    model: str
    messages: list[dict[str, str]] = field(default_factory=list)
    files: list[FileEntry] = field(default_factory=list)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, LiveSession] = {}
        self._cancelled: set[str] = set()
        self._busy: set[str] = set()
        # `chat.cancel` is set from the reader thread while a turn reads it from
        # a worker thread, so the cancel set needs a lock. Sessions themselves
        # stay effectively single-writer (one turn per session at a time).
        self._cancel_lock = threading.Lock()

    def get_or_create(self, session_id: str, model: str) -> LiveSession:
        live = self._sessions.get(session_id)
        if live is None:
            # Try to rehydrate from disk if a session with this name exists.
            prior = None
            try:
                prior = load_session(session_id)
            except Exception:
                prior = None
            if prior is not None:
                files: list[FileEntry] = []
                for fid in prior.file_ids:
                    try:
                        files.append(find_file(fid))
                    except Exception:
                        continue
                live = LiveSession(
                    session_id=session_id,
                    model=prior.model or model,
                    messages=list(prior.messages),
                    files=files,
                )
            else:
                live = LiveSession(session_id=session_id, model=model)
            self._sessions[session_id] = live
        if model:
            live.model = model
        return live

    def set_files(self, session_id: str, files: list[FileEntry]) -> None:
        live = self._sessions.get(session_id)
        if live is not None:
            live.files = files

    def autosave(self, live: LiveSession) -> None:
        sess = Session(
            model=live.model,
            workdir="",  # desktop has no single cwd; sandbox uses a temp dir
            file_ids=[f.id for f in live.files],
            messages=live.messages,
        )
        # Persist under the session_id name and mirror to `last`.
        try:
            save_session(sess, live.session_id)
            save_session(sess, LAST)
        except Exception:
            pass  # best-effort; never crash a turn on a disk hiccup

    # Cancellation ---------------------------------------------------------- #
    def request_cancel(self, session_id: str) -> None:
        with self._cancel_lock:
            self._cancelled.add(session_id)

    def is_cancelled(self, session_id: str) -> bool:
        with self._cancel_lock:
            return session_id in self._cancelled

    def clear_cancel(self, session_id: str) -> None:
        with self._cancel_lock:
            self._cancelled.discard(session_id)

    def is_busy(self, session_id: str) -> bool:
        """True while a streaming turn is in flight for this session."""
        with self._cancel_lock:
            return session_id in self._busy

    def mark_busy(self, session_id: str) -> bool:
        """Claim the session for a turn. False if one is already running.

        Guards against a second `chat.send` arriving mid-turn now that the
        reader thread keeps accepting requests during a turn.
        """
        with self._cancel_lock:
            if session_id in self._busy:
                return False
            self._busy.add(session_id)
            return True

    def clear_busy(self, session_id: str) -> None:
        with self._cancel_lock:
            self._busy.discard(session_id)
