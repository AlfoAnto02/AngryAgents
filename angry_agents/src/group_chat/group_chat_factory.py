from __future__ import annotations

from typing import Literal

from .context_window import ContextWindow
from .scheduler import TurnScheduler
from .session import GroupChatSession


class GroupChatFactory:

    @staticmethod
    def build_session(
        db,
        chat_id: int,
        model: str,
        author_secret: str,
        scheduler_strategy: Literal["round_robin", "weighted_random"] = "weighted_random",
        window_strategy: Literal["rolling", "selective"] = "selective",
        max_messages: int = 40,
    ) -> GroupChatSession:
        from ..agents.personas.factory import AgentFactory
        from ..db.services.group_chat_service import GroupChatService
        from ..db.services.topic_service import TopicService

        chat = GroupChatService(db).get(chat_id)
        topic = TopicService(db).get(chat.id_topic)
        agents = AgentFactory.from_chat_participants(db, chat_id, model)

        scheduler = TurnScheduler(agents, scheduler_strategy)
        context_window = ContextWindow(window_strategy, max_messages)

        return GroupChatSession(
            chat_id=chat_id,
            topic=topic,
            agents=agents,
            scheduler=scheduler,
            context_window=context_window,
            author_secret=author_secret,
        )
