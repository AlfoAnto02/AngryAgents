from ..agent_config import DEFAULT_MODEL, run_persona_identification
from .base_judge import BaseJudge, PersonaIdentificationResult

_PROMPT = """\
You are identifying which agent in a group chat is acting as a specific persona.
Your only lens is IDEOLOGY: political views, values, moral stances, and belief systems.

--- PERSONA PROFILE: {persona_name} ---
{profile_block}

--- MESSAGES BY AUTHOR ---
{messages_block}

Score each author 1–5 on how likely they are acting as {persona_name}, judged only on ideology fit:
  1 = very unlikely  5 = very likely

Reply with one line per author in this exact format:
author_digest: score

Authors to score (in this order): {author_list}
"""


class IdeologyJudge(BaseJudge):
    name = "ideology"
    focus = "political views, values, moral stances, and belief systems"

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model

    def persona_identification(self, chat: dict, personas: list[dict]) -> PersonaIdentificationResult:
        return run_persona_identification(
            lambda name, profile, messages, authors: _PROMPT.format(
                persona_name=name,
                profile_block=profile,
                messages_block=messages,
                author_list=authors,
            ),
            chat, personas, self.model,
        )

    def individual_fidelity(self, _chat: dict) -> None:
        pass

    def group_fidelity(self, _chat: dict) -> None:
        pass

    def behavioural_fidelity(self, _chat: dict) -> None:
        pass
