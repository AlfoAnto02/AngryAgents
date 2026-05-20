from __future__ import annotations

import json
from dataclasses import dataclass, field

from ...db.models.agents import Agent
from ...db.models.agent_context import AgentContext
from ...db.models.chat_messages import ChatMessage
from ...db.models.topic import Topic
from .templates import render_prompt


def _parse_signature_phrases(ctx: AgentContext) -> dict:
    if not ctx.signature_phrases:
        return {}
    try:
        return json.loads(ctx.signature_phrases)
    except (json.JSONDecodeError, TypeError):
        return {}


def _build_profile_block(contexts: list[AgentContext]) -> str:
    sections = []
    for ctx in contexts:
        data = _parse_signature_phrases(ctx)
        for key, value in data.items():
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            sections.append(f"{key}: {value}")
    return "\n".join(sections)


def _extract_dominance_weight(contexts: list[AgentContext]) -> float:
    for ctx in contexts:
        data = _parse_signature_phrases(ctx)
        positioning = data.get("social_positioning", "")
        if isinstance(positioning, str):
            lower = positioning.lower()
            if any(w in lower for w in ("assertive", "dominant", "leader", "outspoken")):
                return 0.7
            if any(w in lower for w in ("reserved", "quiet", "passive", "introverted")):
                return 0.3
    return 0.5


@dataclass
class PersonaAgent:
    agent: Agent
    contexts: list[AgentContext]
    model: str

    _persona_name: str = field(default="", init=False, repr=False)
    _profile_block: str = field(default="", init=False, repr=False)
    _topic_block: str = field(default="", init=False, repr=False)
    dominance_weight: float = field(default=0.5, init=False, repr=False)

    def bind_to_chat(self, _chat_id: int, topic: Topic) -> None:
        self._persona_name = f"{self.agent.name} {self.agent.surname}"
        self._profile_block = _build_profile_block(self.contexts)
        self._topic_block = topic.title
        if topic.description:
            self._topic_block += f": {topic.description}"
        self.dominance_weight = _extract_dominance_weight(self.contexts)

    def respond(self, history: list[ChatMessage], turn_count: int = 0) -> str:
        from ..agent_config import llm_call

        history_block = "\n".join(
            f"[{m.author or 'User'}]: {m.message}" for m in history
        )
        reground = turn_count > 0 and turn_count % 20 == 0
        system, user = render_prompt(
            "persona_chat.j2",
            persona_name=self._persona_name,
            profile_block=self._profile_block,
            topic_block=self._topic_block,
            history_block=history_block,
            reground=reground,
        )
        return llm_call(system, user, self.model)

    def update_summary(self, chat_id: int, _new_message: str, current_summary: dict) -> dict:
        chat_state = current_summary.get(str(chat_id), {})
        chat_state["turn_count"] = chat_state.get("turn_count", 0) + 1
        current_summary[str(chat_id)] = chat_state
        return current_summary
