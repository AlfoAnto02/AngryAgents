import os
import re
from collections import defaultdict

import requests
from dotenv import load_dotenv

from .judges.base_judge import AgentScore, PersonaIdentificationResult

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


def parse_identification_result(raw: str, authors: list[str]) -> PersonaIdentificationResult:
    scores: dict[str, int] = {}
    for line in raw.splitlines():
        m = _LINE_RE.match(line.strip())
        if m:
            scores[m.group(1).strip()] = int(m.group(2))
    return PersonaIdentificationResult(
        scores=[AgentScore(author=a, score=scores.get(a, 1)) for a in authors]
    )


def ollama_chat(prompt: str, model: str, authors: list[str]) -> PersonaIdentificationResult:
    payload = {
        "model": model,
        "stream": False,
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": 0.1, "num_predict": 256},
    }
    resp = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()
    return parse_identification_result(resp.json()["message"]["content"].strip(), authors)
