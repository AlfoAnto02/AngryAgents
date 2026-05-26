import json
import logging
import os
from collections import defaultdict

import requests
from dotenv import load_dotenv

from .judges.base_judge import AuthorMatch, PersonaIdentificationResult, PersonaScore
from .judges.templates import render_prompt

log = logging.getLogger(__name__)

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "mistral")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama")  # "ollama" | "openai"


def format_messages(chat: dict) -> tuple[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for msg in chat["messages"]:
        if not msg.get("author"):
            log.warning("format_messages: skipping message with no author (user-posted)")
            continue
        grouped[msg["author"]].append(msg["message"])
    authors = list(grouped.keys())
    block = "\n\n".join(
        f"[{author}]\n" + "\n".join(f"- {m}" for m in msgs)
        for author, msgs in grouped.items()
    )
    return block, authors


def format_profile(profile: dict) -> str:
    lines = []

    # Style
    if cs := profile.get("core_style"):
        lines.append(f"Style: {cs}")
    if ss := profile.get("speech_signature"):
        lines.append(f"Speech signature: {ss}")
    if humor := profile.get("humor"):
        lines.append(f"Humor: {humor}")

    # Vocabulary — fiction uses vocabulary_fingerprint
    if vf := profile.get("vocabulary_fingerprint"):
        parts = []
        if fw := vf.get("favored_words"):
            parts.append("favored: " + ", ".join(fw))
        if aw := vf.get("avoided_words"):
            parts.append("avoided: " + ", ".join(aw))
        if dj := vf.get("domain_jargon"):
            if dj not in ("none", "None", "", None):
                parts.append(f"jargon: {dj}")
        if fp := vf.get("filler_patterns"):
            if fp not in ("none", "None", "", None):
                parts.append(f"fillers: {fp}")
        if parts:
            lines.append("Vocabulary: " + " | ".join(parts))
    # real_world profiles use vocabulary_markers
    elif vocab := profile.get("vocabulary_markers"):
        lines.append(f"Vocabulary markers: {', '.join(vocab)}")

    # Worldview / ideology — fiction uses worldview, real_world uses ideological_positions
    if wv := profile.get("worldview") or profile.get("ideological_positions"):
        lines.append(f"Worldview: {wv}")
    if si := profile.get("self_image_vs_reality"):
        self_img = si.get("self_image", "")
        reality = si.get("reality", "")
        lines.append(f'Self-image: "{self_img}" (reality: {reality})')

    # Emotional / behavioral
    if kd := profile.get("knowledge_domains"):
        lines.append(f"Knowledge domains: {kd}")
    if rm := profile.get("relationship_matrix"):
        lines.append(f"Relationship matrix: {rm}")
    # fiction: emotional_tells; real_world: emotional_triggers
    if et := profile.get("emotional_tells") or profile.get("emotional_triggers"):
        lines.append(f"Emotional tells: {et}")
    # fiction: situational_behavior; real_world: response_patterns
    if sb := profile.get("situational_behavior") or profile.get("response_patterns"):
        lines.append(f"Situational behavior: {sb}")
    if ep := profile.get("escalation_pattern"):
        lines.append(f"Escalation: {ep}")
    if cg := profile.get("conversation_goals"):
        goals = ", ".join(cg) if isinstance(cg, list) else str(cg)
        lines.append(f"Conversation goals: {goals}")

    # Social positioning
    if sp := profile.get("social_positioning"):
        lines.append(f"Social positioning: {sp}")

    # Quotes — fiction: annotated_quotes; real_world: exemplar_quotes
    quotes = profile.get("annotated_quotes") or profile.get("exemplar_quotes") or []
    if quotes:
        lines.append("Quotes:")
        for q in quotes:
            if isinstance(q, dict):
                ctx = q.get("context", "")
                lines.append(f'  "{q["quote"]}"' + (f"  [{ctx}]" if ctx else ""))
            else:
                lines.append(f'  "{q}"')

    # Do-not-say — negative fingerprint
    dns = profile.get("do_not_say") or []
    if dns:
        entries = []
        for d in dns:
            entries.append(d.get("line", str(d)) if isinstance(d, dict) else str(d))
        lines.append("Would NEVER say: " + " | ".join(f'"{e}"' for e in entries))

    return "\n".join(lines)


def _parse_json_scores(raw: str, authors: list[str]) -> dict[str, int]:
    """Parse LLM JSON output → {author_digest: score} for every author."""
    data = json.loads(raw)
    scores_raw = data.get("scores", {})
    return {a: int(scores_raw.get(a, 1)) for a in authors}


def _ollama_call(system: str, user: str, model: str, *, json_mode: bool = False, temperature: float = 0.85) -> str:
    payload: dict = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {"temperature": temperature, "num_predict": 512},
    }
    if json_mode:
        payload["format"] = "json"
    resp = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=None)
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def _openai_call(system: str, user: str, model: str, *, json_mode: bool = False, temperature: float = 0.85) -> str:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")
    payload: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        json=payload,
        headers=headers,
        timeout=None,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def llm_call(system: str, user: str, model: str, *, json_mode: bool = False, temperature: float = 0.85) -> str:
    if LLM_BACKEND == "openai":
        return _openai_call(system, user, OPENAI_MODEL, json_mode=json_mode, temperature=temperature)
    return _ollama_call(system, user, model, json_mode=json_mode, temperature=temperature)


def run_persona_identification(
    template_name: str,
    chat: dict,
    personas: list[dict],
    model: str,
) -> PersonaIdentificationResult:
    """
    For each persona, call the LLM to score every author in the chat 1-5.
    Then transpose: for each author, return the persona with the highest score.
    """
    messages_block, authors = format_messages(chat)
    if not authors:
        raise ValueError(
            "run_persona_identification: chat has no messages — "
            "check that the chat dict contains a non-empty 'messages' list"
        )
    author_list = ", ".join(authors)

    # author -> list of PersonaScore, one entry per persona
    author_persona_scores: dict[str, list[PersonaScore]] = {a: [] for a in authors}

    for persona in personas:
        name = persona["persona_name"]
        profile_block = format_profile(persona)
        system, user = render_prompt(
            template_name,
            persona_name=name,
            profile_block=profile_block,
            messages_block=messages_block,
            author_list=author_list,
        )
        raw = llm_call(system, user, model, json_mode=True, temperature=0)
        author_scores = _parse_json_scores(raw, authors)
        for author, score in author_scores.items():
            author_persona_scores[author].append(PersonaScore(persona_name=name, score=score))

    matches = [
        AuthorMatch(author=a, scores=author_persona_scores[a])
        for a in authors
    ]
    return PersonaIdentificationResult(matches=matches)
