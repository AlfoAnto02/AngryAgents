from __future__ import annotations

import hashlib
import hmac as _hmac
import random
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional

from ..db.models.chat_messages import ChatMessage
from ..db.models.topic import Topic
from ..agents.personas.persona_agent import PersonaAgent
from .context_window import ContextWindow
from .scheduler import TurnScheduler

if TYPE_CHECKING:
    from ..db.services.chat_messages_service import ChatMessageService


def _agent_token(name: str, surname: str, secret: str) -> str:
    """Reproduce the same HMAC computed by ChatMessageService so we can map tokens → labels."""
    return _hmac.new(
        secret.encode(),
        f"{name}:{surname}".encode(),
        hashlib.sha256,
    ).hexdigest()


@dataclass
class GroupChatSession:
    chat_id: int
    topic: Topic
    agents: list[PersonaAgent]
    scheduler: TurnScheduler
    context_window: ContextWindow
    author_secret: str

    _turn_count: int = field(default=0, init=False, repr=False)
    _author_labels: dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        # Build a stable token → "AgentN" map once; order follows the agents list.
        for i, agent in enumerate(self.agents, 1):
            token = _agent_token(agent.agent.name, agent.agent.surname, self.author_secret)
            self._author_labels[token] = f"Agent{i}"

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

        my_token = _agent_token(agent.agent.name, agent.agent.surname, self.author_secret)
        my_label = self._author_labels.get(my_token, "Agent?")

        last_msg: ChatMessage | None = None

        if agent.message_count > 1:
            # Single LLM call produces all fragments; write them one by one with typing delay
            fragments = agent.respond_burst(
                trimmed,
                turn_count=self._turn_count,
                author_labels=self._author_labels,
                my_label=my_label,
            )
            for i, fragment in enumerate(fragments):
                if stop_check and stop_check():
                    break
                if i > 0:
                    time.sleep(random.uniform(2.0, 4.0))
                last_msg = self._write_message(svc, agent, fragment)
        else:
            content = agent.respond(
                trimmed,
                turn_count=self._turn_count,
                author_labels=self._author_labels,
                my_label=my_label,
            )
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
