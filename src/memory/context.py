from src.memory.session import Session, Turn
from src.llm.prompts import MULTI_TURN_CONTEXT_TEMPLATE, REFERENCE_DETECTION_KEYWORDS
from src.config import CONTEXT_WINDOW_SIZE



class ConversationContextAssembler:
    """
    Assembles conversation history into a prompt-injectable context block.
    Detects when the user is referencing previous turns.
    """

    def is_follow_up(self, prompt: str) -> bool:
        """Detect if the current prompt references previous context."""
        lower = prompt.lower()
        return any(kw in lower for kw in REFERENCE_DETECTION_KEYWORDS)

    def build_context(self, session: Session, current_prompt: str) -> str | None:
        """
        Build conversation context for multi-turn prompts.
        Returns None if this appears to be a standalone query.
        """
        if not session.turns:
            return None

        if not self.is_follow_up(current_prompt):
            return None

        window = session.get_context_window(max_turns=CONTEXT_WINDOW_SIZE)
        history_parts = []

        for turn in window:
            status = "succeeded" if turn.success else "failed"
            part = f"Turn {turn.turn_id}: User asked: \"{turn.user_prompt}\"\n"
            part += f"Status: {status}\n"
            
            if turn.success and turn.generated_code:
                code_preview = turn.generated_code[:500]
                part += f"Generated code:\n```python\n{code_preview}\n```\n"
                
            if turn.execution_output:
                output_preview = turn.execution_output[:300]
                part += f"Output:\n```\n{output_preview}\n```"
                
            history_parts.append(part)

        history = "\n---\n".join(history_parts)

        return MULTI_TURN_CONTEXT_TEMPLATE.format(
            history=history,
            current_prompt=current_prompt,
        )