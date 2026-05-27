from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ..db.models.chat_messages import ChatMessage
    from ..agents.personas.persona_agent import PersonaAgent


class ContextWindow:
    strategy: Literal["rolling", "selective", "full"]
    max_messages: int

    def __init__(self, strategy: Literal["rolling", "selective", "full"] = "full", max_messages: int = 40):
        self.strategy = strategy
        self.max_messages = max_messages

    def trim(self, history: list[ChatMessage], agent: PersonaAgent) -> list[ChatMessage]:
        if self.strategy == "full":
            return history
        if len(history) <= self.max_messages:
            return history
        if self.strategy == "rolling":
            return history[-self.max_messages:]
        k = self.max_messages // 4
        n = self.max_messages - k
        return history[:k] + history[-n:]
