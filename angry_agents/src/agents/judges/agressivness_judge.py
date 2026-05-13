import re

import requests

from .base_judge import BaseJudge, PersonaLikelihood, Verdict

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "mistral"

EVALUATE_PROMPT = """\
You are identifying which persona most likely wrote a message in a group chat.
Your only lens is aggressiveness: how each persona typically uses hostile language, \
provocations, dominance, insults, or blunt assertiveness.

--- PERSONA PROFILES ---
{personas_block}

--- MESSAGE ---
{message}

Score each persona 1–5 on how likely they wrote this message, judged only on aggressiveness fit:
  1 = very unlikely  5 = very likely

Reply with one line per persona in this exact format:
persona_name: score — one sentence reason

Personas to score (in this order): {persona_names}
"""

DELIBERATE_PROMPT = """\
You are identifying which persona most likely wrote a message in a group chat.
Your only lens is aggressiveness.

--- PERSONA PROFILES ---
{personas_block}

--- MESSAGE ---
{message}

--- OTHER JUDGES' VERDICTS ---
{other_verdicts}

Considering the above, give your final likelihood scores.

Reply with one line per persona in this exact format:
persona_name: score — one sentence reason

Personas to score (in this order): {persona_names}
"""

_LINE_RE = re.compile(r"^(.+?):\s*([1-5])\s*[-—]+\s*(.+)$")


def _format_persona(profile: dict) -> str:
    name = profile.get("persona_name", "unknown")
    lines = [f"[{name}]"]
    if style := profile.get("core_style"):
        lines.append(f"Style: {style}")
    if patterns := profile.get("response_patterns", {}):
        if disagreeing := patterns.get("when_disagreeing"):
            lines.append(f"When disagreeing: {disagreeing}")
    if triggers := profile.get("emotional_triggers", {}):
        if negative := triggers.get("negative"):
            lines.append(f"Triggers: {negative}")
    return "\n".join(lines)


def _parse_verdict(raw: str, personas: list[dict]) -> Verdict:
    scores: dict[str, PersonaLikelihood] = {}
    for line in raw.splitlines():
        m = _LINE_RE.match(line.strip())
        if not m:
            continue
        scores[m.group(1).strip()] = PersonaLikelihood(
            persona=m.group(1).strip(),
            score=int(m.group(2)),
            reason=m.group(3).strip(),
        )

    likelihoods = []
    for p in personas:
        name = p["persona_name"]
        likelihoods.append(
            scores.get(name, PersonaLikelihood(persona=name, score=1, reason="not assessed"))
        )
    return Verdict(likelihoods=likelihoods)


def _call(prompt: str, model: str, personas: list[dict]) -> Verdict:
    payload = {
        "model": model,
        "stream": False,
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": 0.1, "num_predict": 512},
    }
    resp = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()
    return _parse_verdict(resp.json()["message"]["content"].strip(), personas)


class AggressivenessJudge(BaseJudge):
    name = "aggressiveness"
    focus = "hostile language, provocations, dominance, insults, and blunt assertiveness"

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model

    def evaluate(self, message: str, personas: list[dict]) -> Verdict:
        prompt = EVALUATE_PROMPT.format(
            personas_block="\n\n".join(_format_persona(p) for p in personas),
            message=message,
            persona_names=", ".join(p["persona_name"] for p in personas),
        )
        return _call(prompt, self.model, personas)

    def deliberate(self, message: str, personas: list[dict], other_verdicts: list[Verdict]) -> Verdict:
        formatted_verdicts = "\n".join(
            f"- {pl.persona}: {pl.score} — {pl.reason}"
            for v in other_verdicts
            for pl in v.likelihoods
        )
        prompt = DELIBERATE_PROMPT.format(
            personas_block="\n\n".join(_format_persona(p) for p in personas),
            message=message,
            other_verdicts=formatted_verdicts,
            persona_names=", ".join(p["persona_name"] for p in personas),
        )
        return _call(prompt, self.model, personas)
