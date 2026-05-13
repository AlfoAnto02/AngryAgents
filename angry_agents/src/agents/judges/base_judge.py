from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PersonaLikelihood:
    persona: str
    score: int   # 1–5: how likely this persona wrote the message
    reason: str


@dataclass
class Verdict:
    likelihoods: list[PersonaLikelihood]

    @property
    def predicted(self) -> str:
        """Persona with the highest likelihood score."""
        return max(self.likelihoods, key=lambda x: x.score).persona


class BaseJudge(ABC):
    """
    Base for all 20 judges.

    Each judge looks at a single message and scores every known persona on how
    likely they are to have written it, through the lens of the judge's focus.

    Example — aggressiveness judge scoring a rude message:
        Trump      → 5  (matches his known aggressive style)
        Winnie     → 1  (far too gentle)

    Phase 1 — independent:   evaluate(message, personas)
    Phase 2 — collaborative: deliberate(message, personas, other_verdicts)
    """

    name: str   # e.g. "aggressiveness", "style", "ideology"
    focus: str  # injected into the prompt to narrow the judge's lens

    @abstractmethod
    def evaluate(self, message: str, personas: list[dict]) -> Verdict:
        """
        Phase 1: score each persona's likelihood of having written this message.
        personas — list of profile dicts (from *_profile.json), each with at
                   least a 'persona_name' key.
        """

    @abstractmethod
    def deliberate(self, message: str, personas: list[dict], other_verdicts: list[Verdict]) -> Verdict:
        """Phase 2: revise or confirm after seeing the other judges' verdicts."""
