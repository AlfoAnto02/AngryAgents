from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

from ..db.models.chat_messages import ChatMessage
from ..db.models.topic import Topic
from ..agents.personas.persona_agent import PersonaAgent
from .context_window import ContextWindow
from .scheduler import TurnScheduler

_SUMMARY_UPDATE_EVERY = 10


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

    def run_turn(self, db) -> ChatMessage:
        from ..db.services.chat_messages_service import ChatMessageService
        from ..db.services.agents_service import AgentService

        svc = ChatMessageService(db, self.author_secret)
        agent = self.scheduler.next()

        last_msg: ChatMessage | None = None
        for _ in range(agent.burst_size):
            self._turn_count += 1

            history: list[ChatMessage] = svc.query(filters={"id_chat": self.chat_id})
            trimmed = self.context_window.trim(history, agent)

            content = agent.respond(trimmed, turn_count=self._turn_count)
            last_msg = self._write_message(svc, agent, content)

            if self._turn_count % _SUMMARY_UPDATE_EVERY == 0:
                current_summary = json.loads(agent.agent.summary or "{}")
                new_summary = agent.update_summary(self.chat_id, content, current_summary)
                AgentService(db).update(agent.agent.id, {"summary": json.dumps(new_summary)})

        self.scheduler.mark_spoke(agent)
        return last_msg  # type: ignore[return-value]  # burst_size >= 1 always

    def _write_message(self, svc: ChatMessageService, agent: PersonaAgent, content: str) -> ChatMessage:
        return svc.create(
            id_chat=self.chat_id,
            message=content,
            agent_id=agent.agent.id,
            created_by=None,
        )
