import re

import requests

from .base_judge import AgentScore, BaseJudge, PersonaIdentificationResult

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "mistral"

PERSONA_ID_PROMPT = """\
You are identifying which agent most likely wrote each message in a group chat.
Your only lens is style: vocabulary, sentence structure, tone, and rhetorical habits.

--- MESSAGES BY AUTHOR ---
{messages_block}

Score each author 1–5 on how identifiable their stylistic voice is:
  1 = very unclear  5 = very distinctive

Reply with one line per author in this exact format:
author_digest: score

Authors to score (in this order): {author_list}
"""

_LINE_RE = re.compile(r"^(.+?):\s*([1-5])\s*$")


def _format_messages(chat: dict) -> tuple[str, list[str]]:
    from collections import defaultdict
    grouped: dict[str, list[str]] = defaultdict(list)
    for msg in chat["messages"]:
        grouped[msg["author"]].append(msg["message"])
    authors = list(grouped.keys())
    block = "\n\n".join(
        f"[{author}]\n" + "\n".join(f"- {m}" for m in msgs)
        for author, msgs in grouped.items()
    )
    return block, authors


def _parse_result(raw: str, authors: list[str]) -> PersonaIdentificationResult:
    scores: dict[str, int] = {}
    for line in raw.splitlines():
        m = _LINE_RE.match(line.strip())
        if m:
            scores[m.group(1).strip()] = int(m.group(2))
    return PersonaIdentificationResult(
        scores=[AgentScore(author=a, score=scores.get(a, 1)) for a in authors]
    )


def _call(prompt: str, model: str, authors: list[str]) -> PersonaIdentificationResult:
    payload = {
        "model": model,
        "stream": False,
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": 0.1, "num_predict": 256},
    }
    resp = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()
    return _parse_result(resp.json()["message"]["content"].strip(), authors)


class StyleJudge(BaseJudge):
    name = "style"
    focus = "vocabulary, sentence structure, tone, and rhetorical habits"

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model

    def persona_identification(self, chat: dict) -> PersonaIdentificationResult:
        messages_block, authors = _format_messages(chat)
        prompt = PERSONA_ID_PROMPT.format(
            messages_block=messages_block,
            author_list=", ".join(authors),
        )
        return _call(prompt, self.model, authors)

    def individual_fidelity(self, _chat: dict) -> None:
        pass

    def group_fidelity(self, _chat: dict) -> None:
        pass

    def behavioural_fidelity(self, _chat: dict) -> None:
        pass
