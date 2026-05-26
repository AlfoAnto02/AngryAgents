from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..db.models.chat_messages import ChatMessage
from ..db.models.topic import Topic
from ..agents.personas.persona_agent import PersonaAgent
from .context_window import ContextWindow
from .scheduler import TurnScheduler


@dataclass
class GroupChatSession:
    chat_id: int
    topic: Topic
    agents: list[PersonaAgent]
    scheduler: TurnScheduler
    context_window: ContextWindow
    author_secret: str

    _turn_count: int = field(default=0, init=False, repr=False)

    def run(
        self,
        db,
        n_turns: int,
        on_message: Callable[[ChatMessage], None] | None = None,
    ) -> list[ChatMessage]:
        produced = []
        for _ in range(n_turns):
            msg = self.run_turn(db)
            produced.append(msg)
            if on_message:
                on_message(msg)
        return produced

    def run_turn(
        self,
        db,
        stop_check: Optional[Callable[[], bool]] = None,
    ) -> ChatMessage | None:
        from ..db.services.chat_messages_service import ChatMessageService

        svc = ChatMessageService(db, self.author_secret)
        agent = self.scheduler.next()
        self._turn_count += 1

        history: list[ChatMessage] = svc.query(filters={"id_chat": self.chat_id})
        trimmed = self.context_window.trim(history, agent)

        last_msg: ChatMessage | None = None

        if agent.burst_size > 1:
            # Single LLM call produces all fragments; write them one by one with typing delay
            fragments = agent.respond_burst(trimmed, turn_count=self._turn_count)
            for i, fragment in enumerate(fragments):
                if stop_check and stop_check():
                    break
                if i > 0:
                    time.sleep(random.uniform(2.0, 4.0))
                last_msg = self._write_message(svc, agent, fragment)
        else:
            content = agent.respond(trimmed, turn_count=self._turn_count)
            last_msg = self._write_message(svc, agent, content)

        self.scheduler.mark_spoke(agent)
        return last_msg

    def _write_message(self, svc: ChatMessageService, agent: PersonaAgent, content: str) -> ChatMessage:
        return svc.create(
            id_chat=self.chat_id,
            message=content,
            agent_id=agent.agent.id,
            created_by=None,
        )
