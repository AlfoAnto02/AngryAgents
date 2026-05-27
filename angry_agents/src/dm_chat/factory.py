from __future__ import annotations

from typing import Literal

from .session import DMSession
from ..group_chat.context_window import ContextWindow


class DMFactory:

    @staticmethod
    def build_session(
        db,
        chat_id: int,
        model: str,
        author_secret: str,
        window_strategy: Literal["rolling", "selective", "full"] = "full",
        max_messages: int = 40,
    ) -> DMSession:
        from ..agents.personas.factory import AgentFactory
        from ..db.services.group_chat_service import GroupChatService
        from ..db.services.topic_service import TopicService

        chat = GroupChatService(db).get(chat_id)
        if chat is None:
            raise ValueError(f"DM chat {chat_id} not found")

        topic = TopicService(db).get(chat.id_topic)

        row = db.execute(
            """SELECT a.ID FROM Chat_agent ca
               JOIN Agents a ON ca.id_agent = a.ID
               WHERE ca.id_chat = ? AND a.deleted_at IS NULL
               LIMIT 1""",
            (chat_id,),
        ).fetchone()

        if row is None:
            raise ValueError(f"No agent found for DM chat {chat_id}")

        agent = AgentFactory.from_db(db, row["ID"], model)
        if topic:
            agent.bind_to_chat(chat_id, topic, template_name="persona_chat.j2")

        return DMSession(
            chat_id=chat_id,
            topic=topic,
            agent=agent,
            context_window=ContextWindow(window_strategy, max_messages),
            author_secret=author_secret,
        )
