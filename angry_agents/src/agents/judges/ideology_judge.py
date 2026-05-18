from ..agent_config import DEFAULT_MODEL, format_messages, ollama_chat
from .base_judge import BaseJudge, PersonaIdentificationResult

PERSONA_ID_PROMPT = """\
You are identifying which agent most likely wrote each message in a group chat.
Your only lens is ideology: political views, values, moral stances, and belief systems.

--- MESSAGES BY AUTHOR ---
{messages_block}

Score each author 1–5 on how identifiable their ideological voice is:
  1 = very unclear  5 = very distinctive

Reply with one line per author in this exact format:
author_digest: score

Authors to score (in this order): {author_list}
"""


class IdeologyJudge(BaseJudge):
    name = "ideology"
    focus = "political views, values, moral stances, and belief systems"

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model

    def persona_identification(self, chat: dict) -> PersonaIdentificationResult:
        messages_block, authors = format_messages(chat)
        prompt = PERSONA_ID_PROMPT.format(
            messages_block=messages_block,
            author_list=", ".join(authors),
        )
        return ollama_chat(prompt, self.model, authors)

    def individual_fidelity(self, _chat: dict) -> None:
        pass

    def group_fidelity(self, _chat: dict) -> None:
        pass

    def behavioural_fidelity(self, _chat: dict) -> None:
        pass
