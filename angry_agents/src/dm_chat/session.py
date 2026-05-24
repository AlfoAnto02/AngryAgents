from __future__ import annotations

from dataclasses import dataclass

from ..db.models.chat_messages import ChatMessage
from ..db.models.topic import Topic
from ..agents.personas.persona_agent import PersonaAgent
from ..group_chat.context_window import ContextWindow


@dataclass
class DMSession:
    chat_id: int
    topic: Topic
    agent: PersonaAgent
    context_window: ContextWindow
    author_secret: str

    def respond(self, db) -> ChatMessage:
        from ..db.services.chat_messages_service import ChatMessageService

        svc = ChatMessageService(db, self.author_secret)
        history: list[ChatMessage] = svc.query(filters={"id_chat": self.chat_id})
        trimmed = self.context_window.trim(history, self.agent)
        content = self.agent.respond(trimmed)
        return svc.create(
            id_chat=self.chat_id,
            message=content,
            agent_id=self.agent.agent.id,
            created_by=None,
        )
