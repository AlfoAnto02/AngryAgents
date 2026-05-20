from __future__ import annotations

from .persona_agent import PersonaAgent


class AgentFactory:

    @staticmethod
    def from_db(db, agent_id: int, model: str) -> PersonaAgent:
        from ...db.services.agents_service import AgentService
        from ...db.services.agent_context_service import AgentContextService

        agent = AgentService(db).get(agent_id)
        contexts = AgentContextService(db).query(filters={"id_agent": agent_id})
        return PersonaAgent(agent=agent, contexts=contexts, model=model)

    @staticmethod
    def for_chat(db, chat_id: int, model: str) -> list[PersonaAgent]:
        """Get agents for a chat by topic (used by eval pipeline)."""
        from ...db.services.group_chat_service import GroupChatService
        from ...db.services.agents_service import AgentService
        from ...db.services.topic_service import TopicService

        chat = GroupChatService(db).get(chat_id)
        topic = TopicService(db).get(chat.id_topic)
        agent_rows = AgentService(db).query(filters={"id_topic": chat.id_topic})

        agents = []
        for row in agent_rows:
            agent = AgentFactory.from_db(db, row.id, model)
            agent.bind_to_chat(chat_id, topic)
            agents.append(agent)
        return agents

    @staticmethod
    def from_chat_participants(db, chat_id: int, model: str) -> list[PersonaAgent]:
        """Get agents for a chat from the Chat_agent join table (used by UI)."""
        from ...db.services.group_chat_service import GroupChatService
        from ...db.services.topic_service import TopicService

        chat = GroupChatService(db).get(chat_id)
        if chat is None:
            return []
        topic = TopicService(db).get(chat.id_topic)

        rows = db.execute(
            """SELECT a.ID FROM Chat_agent ca
               JOIN Agents a ON ca.id_agent = a.ID
               WHERE ca.id_chat = ? AND a.deleted_at IS NULL""",
            (chat_id,),
        ).fetchall()

        agents = []
        for row in rows:
            agent = AgentFactory.from_db(db, row["ID"], model)
            if topic:
                agent.bind_to_chat(chat_id, topic)
            agents.append(agent)
        return agents
