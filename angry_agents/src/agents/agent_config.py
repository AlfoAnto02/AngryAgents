import os
import re
from collections import defaultdict
from typing import Callable

import requests
from dotenv import load_dotenv

from .judges.base_judge import AgentScore, PersonaIdentificationResult, PersonaMatch

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "mistral")

_LINE_RE = re.compile(r"^(.+?):\s*([1-5])\s*$")


def format_messages(chat: dict) -> tuple[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for msg in chat["messages"]:
        grouped[msg["author"]].append(msg["message"])
    authors = list(grouped.keys())
    block = "\n\n".join(
        f"[{author}]\n" + "\n".join(f"- {m}" for m in msgs)
        for author, msgs in grouped.items()
    )
    return block, authors


def format_profile(profile: dict) -> str:
    lines = []
    if style := profile.get("core_style"):
        lines.append(f"Style: {style}")
    if humor := profile.get("humor"):
        lines.append(f"Humor: {humor}")
    if vocab := profile.get("vocabulary_markers"):
        lines.append(f"Vocabulary markers: {', '.join(vocab)}")
    if ideology := profile.get("ideological_positions"):
        lines.append(f"Ideology: {ideology}")
    if triggers := profile.get("emotional_triggers"):
        lines.append(f"Triggers: {triggers}")
    if patterns := profile.get("response_patterns"):
        lines.append(f"Response patterns: {patterns}")
    if social := profile.get("social_positioning"):
        lines.append(f"Social positioning: {social}")
    if quotes := profile.get("exemplar_quotes"):
        lines.append("Exemplar quotes:")
        lines.extend(f'  "{q}"' for q in quotes)
    return "\n".join(lines)


def _parse_agent_scores(raw: str, authors: list[str]) -> list[AgentScore]:
    scores: dict[str, int] = {}
    for line in raw.splitlines():
        m = _LINE_RE.match(line.strip())
        if m:
            scores[m.group(1).strip()] = int(m.group(2))
    return [AgentScore(author=a, score=scores.get(a, 1)) for a in authors]


def _ollama_call(prompt: str, model: str) -> str:
    payload = {
        "model": model,
        "stream": False,
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": 0.1, "num_predict": 256},
    }
    resp = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def run_persona_identification(
    build_prompt: Callable[[str, str, str, str], str],
    chat: dict,
    personas: list[dict],
    model: str,
) -> PersonaIdentificationResult:
    """
    For each persona, call the LLM to score every agent in the chat.
    build_prompt(persona_name, profile_block, messages_block, author_list) → prompt str.
    """
    messages_block, authors = format_messages(chat)
    author_list = ", ".join(authors)
    matches = []
    for persona in personas:
        name = persona["persona_name"]
        profile_block = format_profile(persona)
        prompt = build_prompt(name, profile_block, messages_block, author_list)
        raw = _ollama_call(prompt, model)
        scores = _parse_agent_scores(raw, authors)
        matches.append(PersonaMatch(persona_name=name, scores=scores))
    return PersonaIdentificationResult(matches=matches)
