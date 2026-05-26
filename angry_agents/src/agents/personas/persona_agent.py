from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from ...db.models.agents import Agent
from ...db.models.agent_context import AgentContext
from ...db.models.chat_messages import ChatMessage
from ...db.models.topic import Topic
from .templates import render_prompt

log = logging.getLogger(__name__)

_SKIP_KEYS = {"persona_name", "source_type", "source_title", "annotated_quotes", "do_not_say"}


def _parse_signature_phrases(ctx: AgentContext) -> dict:
    if not ctx.signature_phrases:
        return {}
    try:
        return json.loads(ctx.signature_phrases)
    except (json.JSONDecodeError, TypeError):
        return {}


def _get_profile_dict(contexts: list[AgentContext], agent: Agent | None = None) -> dict:
    """Return profile dict from AgentContext.signature_phrases; fall back to Agent.summary."""
    for ctx in contexts:
        data = _parse_signature_phrases(ctx)
        if data:
            log.debug("profile_source | using AgentContext id=%s", ctx.id_context)
            return data
    if agent and agent.summary:
        try:
            data = json.loads(agent.summary)
            log.info("profile_source | agent=%s fell back to Agent.summary (no AgentContext rows)", getattr(agent, "id", "?"))
            return data
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


def _flatten_value(value) -> str:
    if isinstance(value, list):
        return ", ".join(
            _flatten_value(v) if isinstance(v, (dict, list)) else str(v) for v in value
        )
    if isinstance(value, dict):
        return "; ".join(
            f"{k}: {v}" for k, v in value.items() if not isinstance(v, (dict, list))
        )
    return str(value)


def _log_profile_build(agent_name: str, source: str, data: dict, result: str) -> None:
    if not result.strip():
        log.warning(
            "profile_build | agent=%s → EMPTY profile block (source=%s, data_keys=%s)",
            agent_name, source, list(data.keys()),
        )
    else:
        log.info(
            "profile_build | agent=%s source=%s chars=%d keys=%s",
            agent_name, source, len(result), list(data.keys())[:6],
        )
        log.debug("profile_build | agent=%s → first 300 chars:\n%s", agent_name, result[:300])


def _build_profile_block(
    contexts: list[AgentContext],
    agent_name: str = "",
    agent: Agent | None = None,
) -> str:
    data = _get_profile_dict(contexts, agent)
    source = "agent.summary" if (not contexts and agent and agent.summary) else "AgentContext"
    sections = []
    for key, value in data.items():
        if key in _SKIP_KEYS:
            continue
        if isinstance(value, dict):
            for sub_key, sub_val in value.items():
                sections.append(f"{key}.{sub_key}: {_flatten_value(sub_val)}")
        else:
            sections.append(f"{key}: {_flatten_value(value)}")
    result = "\n".join(sections)
    _log_profile_build(agent_name, source, data, result)
    return result


def _extract_dominance_weight(contexts: list[AgentContext], agent: Agent | None = None) -> float:
    data = _get_profile_dict(contexts, agent)
    positioning = data.get("social_positioning", "")
    if isinstance(positioning, dict):
        positioning = " ".join(str(v) for v in positioning.values())
    if isinstance(positioning, str):
        lower = positioning.lower()
        if any(w in lower for w in ("assertive", "dominant", "leader", "outspoken")):
            return 0.7
        if any(w in lower for w in ("reserved", "quiet", "passive", "introverted")):
            return 0.3
    return 0.5


def _extract_cooldown_turns(contexts: list[AgentContext], agent: Agent | None = None) -> int:
    data = _get_profile_dict(contexts, agent)
    core_style = data.get("core_style", {})
    if isinstance(core_style, dict):
        rhythm = core_style.get("rhythm", "").lower()
        if any(w in rhythm for w in ("fast", "staccato", "rapid", "quick", "associative")):
            return 3
        if any(w in rhythm for w in ("slow", "deliberate", "lecture", "measured", "methodical")):
            return 6
    return 4


def _extract_burst_size(contexts: list[AgentContext], agent: Agent | None = None) -> int:
    data = _get_profile_dict(contexts, agent)
    core_style = data.get("core_style", {})
    if isinstance(core_style, dict):
        rhythm = core_style.get("rhythm", "").lower()
        if any(w in rhythm for w in ("fast", "staccato")):
            return 3
        if "slow" in rhythm:
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
        self._profile_block = _build_profile_block(
            self.contexts, agent_name=self._persona_name, agent=self.agent
        )

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
        self.dominance_weight = _extract_dominance_weight(self.contexts, self.agent)
        self.cooldown_turns = _extract_cooldown_turns(self.contexts, self.agent)
        self.burst_size = _extract_burst_size(self.contexts, self.agent)

    def _render(self, history: list[ChatMessage], turn_count: int) -> tuple[str, str]:
        history_block = "\n".join(
            f"[{m.author or 'User'}]: {m.message}" for m in history
        )
        reground = turn_count > 0 and turn_count % 20 == 0
        return render_prompt(
            self._template_name,
            persona_name=self._persona_name,
            profile_block=self._profile_block,
            topic_block=self._topic_block,
            history_block=history_block,
            reground=reground,
            burst_size=self.burst_size,
        )

    def respond(self, history: list[ChatMessage], turn_count: int = 0) -> str:
        from ..agent_config import llm_call

        system, user = self._render(history, turn_count)
        return llm_call(system, user, self.model)

    def respond_burst(self, history: list[ChatMessage], turn_count: int = 0) -> list[str]:
        import re
        from ..agent_config import llm_call

        system, user = self._render(history, turn_count)
        raw = llm_call(system, user, self.model)
        fragments = re.findall(r'\[\d+\]\s*(.+?)(?=\s*\[\d+\]|$)', raw, re.DOTALL)
        cleaned = [f.strip() for f in fragments if f.strip()]
        return cleaned if cleaned else [raw.strip()]
