from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..db.models.chat_messages import ChatMessage
from ..db.models.topic import Topic
from ..agents.personas.persona_agent import PersonaAgent
from ..group_chat.context_window import ContextWindow

if TYPE_CHECKING:
    from ..db.services.chat_messages_service import ChatMessageService


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

        fragments = self.agent.respond_burst(trimmed)
        last_msg: ChatMessage | None = None
        for i, fragment in enumerate(fragments):
            if i > 0:
                time.sleep(random.uniform(1.5, 3.0))
            last_msg = svc.create(
                id_chat=self.chat_id,
                message=fragment,
                agent_id=self.agent.agent.id,
                created_by=None,
            )
        return last_msg
