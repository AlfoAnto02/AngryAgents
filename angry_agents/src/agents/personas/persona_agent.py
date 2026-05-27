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


def _calculate_message_count(contexts: list[AgentContext], agent: Agent | None = None) -> int:
    """Score-based derivation of how many messages the agent sends per turn.

    Signals (additive):
      rhythm fast/staccato  → +2   (primary)
      rhythm slow           → -2   (primary)
      sentence_shape short/clipped/staccato/declarative/interrupted → +1
      sentence_shape long/flowing/elaborate/extended                → -1
      filler_patterns contains rapid/interruption/burst             → +1

    Thresholds: score ≥ 3 → 3 messages, score ≥ 1 → 2 messages, else → 1 message.
    """
    data = _get_profile_dict(contexts, agent)
    score = 0

    core = data.get("core_style", {})
    if isinstance(core, dict):
        rhythm = core.get("rhythm", "").lower()
        if any(w in rhythm for w in ("fast", "staccato")):
            score += 2
        elif any(w in rhythm for w in ("slow", "deliberate")):
            score -= 2

        shape = core.get("sentence_shape", "").lower()
        if any(w in shape for w in ("short", "staccato", "sharp", "clipped", "declarative", "interrupted", "punchy")):
            score += 1
        elif any(w in shape for w in ("long", "flowing", "elaborate", "extended")):
            score -= 1

    vocab = data.get("vocabulary_fingerprint", {})
    if isinstance(vocab, dict):
        fillers = vocab.get("filler_patterns", "").lower()
        if any(w in fillers for w in ("rapid", "interruption", "burst", "quick")):
            score += 1

    if score >= 3:
        return 3
    if score >= 1:
        return 2
    return 1


def _extract_sentence_shape(contexts: list[AgentContext], agent: Agent | None = None) -> str:
    data = _get_profile_dict(contexts, agent)
    core = data.get("core_style", {})
    return core.get("sentence_shape", "") if isinstance(core, dict) else ""


def _extract_humor(contexts: list[AgentContext], agent: Agent | None = None) -> tuple[str, str]:
    data = _get_profile_dict(contexts, agent)
    humor = data.get("humor", {})
    if isinstance(humor, dict):
        return humor.get("frequency", ""), humor.get("style", "")
    return "", ""


def _extract_filler_patterns(contexts: list[AgentContext], agent: Agent | None = None) -> str:
    data = _get_profile_dict(contexts, agent)
    vocab = data.get("vocabulary_fingerprint", {})
    return vocab.get("filler_patterns", "") if isinstance(vocab, dict) else ""


def _extract_avoided_words(contexts: list[AgentContext], agent: Agent | None = None) -> list[str]:
    data = _get_profile_dict(contexts, agent)
    vocab = data.get("vocabulary_fingerprint", {})
    if isinstance(vocab, dict):
        words = vocab.get("avoided_words", [])
        return words if isinstance(words, list) else []
    return []


def _extract_structural_patterns(contexts: list[AgentContext], agent: Agent | None = None) -> list[str]:
    data = _get_profile_dict(contexts, agent)
    sig = data.get("speech_signature", {})
    if isinstance(sig, dict):
        patterns = sig.get("structural_patterns", [])
        return patterns if isinstance(patterns, list) else []
    return []


def _extract_conversation_goals(contexts: list[AgentContext], agent: Agent | None = None) -> list[str]:
    data = _get_profile_dict(contexts, agent)
    goals = data.get("conversation_goals", [])
    return goals if isinstance(goals, list) else []


def _extract_escalation_pattern(contexts: list[AgentContext], agent: Agent | None = None) -> str:
    data = _get_profile_dict(contexts, agent)
    pattern = data.get("escalation_pattern", "")
    return pattern if isinstance(pattern, str) else ""


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
    message_count: int = field(default=1, init=False, repr=False)
    # Style fields — extracted once at bind_to_chat(), passed to templates as variables
    _sentence_shape: str = field(default="", init=False, repr=False)
    _humor_frequency: str = field(default="", init=False, repr=False)
    _humor_style: str = field(default="", init=False, repr=False)
    _filler_patterns: str = field(default="", init=False, repr=False)
    _avoided_words: list[str] = field(default_factory=list, init=False, repr=False)
    _structural_patterns: list[str] = field(default_factory=list, init=False, repr=False)
    _conversation_goals: list[str] = field(default_factory=list, init=False, repr=False)
    _escalation_pattern: str = field(default="", init=False, repr=False)

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
        self.message_count = _calculate_message_count(self.contexts, self.agent)
        self._sentence_shape = _extract_sentence_shape(self.contexts, self.agent)
        self._humor_frequency, self._humor_style = _extract_humor(self.contexts, self.agent)
        self._filler_patterns = _extract_filler_patterns(self.contexts, self.agent)
        self._avoided_words = _extract_avoided_words(self.contexts, self.agent)
        self._structural_patterns = _extract_structural_patterns(self.contexts, self.agent)
        self._conversation_goals = _extract_conversation_goals(self.contexts, self.agent)
        self._escalation_pattern = _extract_escalation_pattern(self.contexts, self.agent)

    def _render(
        self,
        history: list[ChatMessage],
        turn_count: int,
        author_labels: dict[str, str] | None = None,
        my_label: str = "You",
    ) -> tuple[str, str]:
        labels = author_labels or {}
        history_block = "\n".join(
            f"[{labels.get(m.author, m.author) if m.author else 'User'}]: {m.message}"
            for m in history
        )
        reground = turn_count > 0 and turn_count % 20 == 0
        return render_prompt(
            self._template_name,
            persona_name=self._persona_name,
            profile_block=self._profile_block,
            topic_block=self._topic_block,
            history_block=history_block,
            reground=reground,
            message_count=self.message_count,
            agent_label=my_label,
            sentence_shape=self._sentence_shape,
            humor_frequency=self._humor_frequency,
            humor_style=self._humor_style,
            filler_patterns=self._filler_patterns,
            avoided_words=self._avoided_words,
            structural_patterns=self._structural_patterns,
            conversation_goals=self._conversation_goals,
            escalation_pattern=self._escalation_pattern,
        )

    def respond(
        self,
        history: list[ChatMessage],
        turn_count: int = 0,
        author_labels: dict[str, str] | None = None,
        my_label: str = "You",
    ) -> str:
        from ..agent_config import llm_call

        system, user = self._render(history, turn_count, author_labels, my_label)
        return llm_call(system, user, self.model)

    def respond_burst(
        self,
        history: list[ChatMessage],
        turn_count: int = 0,
        author_labels: dict[str, str] | None = None,
        my_label: str = "You",
    ) -> list[str]:
        import re
        from ..agent_config import llm_call

        system, user = self._render(history, turn_count, author_labels, my_label)
        raw = llm_call(system, user, self.model)
        fragments = re.findall(r'\[\d+\]\s*(.+?)(?=\s*\[\d+\]|$)', raw, re.DOTALL)
        cleaned = [f.strip() for f in fragments if f.strip()]
        return cleaned if cleaned else [raw.strip()]
