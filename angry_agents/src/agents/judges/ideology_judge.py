from ..agent_config import DEFAULT_MODEL, run_persona_identification
from .base_judge import BaseJudge, PersonaIdentificationResult


class IdeologyJudge(BaseJudge):
    name = "ideology"
    focus = "political views, values, moral stances, and belief systems"

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model

    def persona_identification(self, chat: dict, personas: list[dict]) -> PersonaIdentificationResult:
        return run_persona_identification("persona_id_ideology.j2", chat, personas, self.model)

    def individual_fidelity(self, _chat: dict) -> None:
        pass

    def group_fidelity(self, _chat: dict) -> None:
        pass

    def behavioural_fidelity(self, _chat: dict) -> None:
        pass
