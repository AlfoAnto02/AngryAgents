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
        # fiction profiles store social_positioning as a dict
        if isinstance(positioning, dict):
            positioning = " ".join(str(v) for v in positioning.values())
        if isinstance(positioning, str):
            lower = positioning.lower()
            if any(w in lower for w in ("assertive", "dominant", "leader", "outspoken")):
                return 0.7
            if any(w in lower for w in ("reserved", "quiet", "passive", "introverted")):
                return 0.3
    return 0.5


def _extract_cooldown_turns(contexts: list[AgentContext]) -> int:
    for ctx in contexts:
        data = _parse_signature_phrases(ctx)
        core_style = data.get("core_style", {})
        if not isinstance(core_style, dict):
            continue
        rhythm = core_style.get("rhythm", "").lower()
        if any(w in rhythm for w in ("fast", "staccato", "rapid", "quick", "associative")):
            return 1
        if any(w in rhythm for w in ("slow", "deliberate", "lecture", "measured", "methodical")):
            return 6
    return 3


def _extract_burst_size(contexts: list[AgentContext]) -> int:
    for ctx in contexts:
        data = _parse_signature_phrases(ctx)
        core_style = data.get("core_style", {})
        if not isinstance(core_style, dict):
            continue
        shape = core_style.get("sentence_shape", "").lower()
        if any(w in shape for w in ("clipped", "fragment", "short", "staccato", "terse")):
            return 3
        if any(w in shape for w in ("compound", "rhetorical", "long", "elaborate", "extended", "run")):
            return 1
    return 2


@dataclass
class PersonaAgent:
    agent: Agent
    contexts: list[AgentContext]
    model: str

    _persona_name: str = field(default="", init=False, repr=False)
    _profile_block: str = field(default="", init=False, repr=False)
    _topic_block: str = field(default="", init=False, repr=False)
    _template_name: str = field(default="group_persona_chat.j2", init=False, repr=False)
    dominance_weight: float = field(default=0.5, init=False, repr=False)
    cooldown_turns: int = field(default=3, init=False, repr=False)
    burst_size: int = field(default=2, init=False, repr=False)

    def bind_to_chat(
        self,
        _chat_id: int,
        topic: Topic,
        template_name: str = "group_persona_chat.j2",
    ) -> None:
        self._persona_name = f"{self.agent.name} {self.agent.surname}"
        self._profile_block = _build_profile_block(self.contexts)

        # topic.title carries a unique "__<timestamp>" suffix; topic.description
        # holds a JSON blob {"title": <clean>, "topics": [...], "tone": "..."}.
        # Prefer the clean title from the JSON so agents receive a readable prompt.
        topic_title = topic.title
        if topic.description:
            try:
                meta = json.loads(topic.description)
                if isinstance(meta, dict) and meta.get("title"):
                    topic_title = meta["title"]
            except (json.JSONDecodeError, TypeError):
                pass
        self._topic_block = topic_title

        self._template_name = template_name
        self.dominance_weight = _extract_dominance_weight(self.contexts)
        self.cooldown_turns = _extract_cooldown_turns(self.contexts)
        self.burst_size = _extract_burst_size(self.contexts)

    def respond(self, history: list[ChatMessage], turn_count: int = 0) -> str:
        from ..agent_config import llm_call

        history_block = "\n".join(
            f"[{m.author or 'User'}]: {m.message}" for m in history
        )
        reground = turn_count > 0 and turn_count % 20 == 0
        system, user = render_prompt(
            self._template_name,
            persona_name=self._persona_name,
            profile_block=self._profile_block,
            topic_block=self._topic_block,
            history_block=history_block,
            reground=reground,
        )
        return llm_call(system, user, self.model)

