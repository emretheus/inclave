import uuid
import time
from dataclasses import dataclass, field
from src.config import SESSION_TTL

@dataclass
class Turn:
    turn_id: int
    user_prompt: str
    query_category: str
    generated_code: str
    execution_output: str
    success: bool
    timestamp: float = field(default_factory=time.time)

@dataclass
class Session:
    session_id: str
    csv_path: str
    csv_schema_str: str
    turns: list[Turn] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    @property
    def last_turn(self) -> Turn | None:
        return self.turns[-1] if self.turns else None

    @property
    def last_successful_turn(self) -> Turn | None:
        for turn in reversed(self.turns):
            if turn.success:
                return turn
        return None

    def add_turn(self, **kwargs) -> Turn:
        turn = Turn(turn_id=self.turn_count + 1, **kwargs)
        self.turns.append(turn)
        return turn

    def get_context_window(self, max_turns: int = 3) -> list[Turn]:
        """Return the last N turns for context injection."""
        return self.turns[-max_turns:]

class SessionManager:
    """
    Manages conversation sessions. In-memory for MVP,
    can be backed by Redis or a database later.
    """

    MAX_SESSIONS = 100
    
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create_session(self, csv_path: str, csv_schema_str: str) -> Session:
        """Create a new conversation session."""
        self._cleanup_expired()

        session_id = str(uuid.uuid4())[:8]
        session = Session(
            session_id=session_id,
            csv_path=csv_path,
            csv_schema_str=csv_schema_str,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session and (time.time() - session.created_at) > SESSION_TTL:
            del self._sessions[session_id]
            return None
        return session

    def _cleanup_expired(self):
        """Remove expired sessions and enforce max limit."""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if (now - s.created_at) > SESSION_TTL
        ]
        for sid in expired:
            del self._sessions[sid]

        if len(self._sessions) >= self.MAX_SESSIONS:
            oldest = min(self._sessions.values(), key=lambda s: s.created_at)
            del self._sessions[oldest.session_id]

    def list_sessions(self) -> list[dict]:
        return [
            {
                "session_id": s.session_id,
                "csv_path": s.csv_path,
                "turns": s.turn_count,
                "created_at": s.created_at,
            }
            for s in self._sessions.values()
        ]