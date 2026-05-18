from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AgentScore:
    author: str   # anonymised DIGEST from Chat_messages
    score: int    # 1–5


@dataclass
class PersonaIdentificationResult:
    scores: list[AgentScore]

    @property
    def predicted(self) -> str:
        """Author with the highest identification score."""
        return max(self.scores, key=lambda x: x.score).author


class BaseJudge(ABC):
    """
    Base for all 20 judges.

    Each judge evaluates a full Group_chat across four dimensions.
    The judge's focus (style, ideology, general, behavioral) narrows
    the lens for every evaluation.

    Phase 1 — independent:   all four evaluate() methods
    Phase 2 — collaborative: judges see each other's outputs and revise
    """

    name: str   # e.g. "aggressiveness", "style", "ideology"
    focus: str  # injected into the prompt to narrow the judge's lens

    @abstractmethod
    def persona_identification(self, chat: dict) -> PersonaIdentificationResult:
        """
        Score each agent in the chat 1–5 on how identifiable their persona is,
        then return the argmax's result(predicted author).

        chat — the full Group_chat dict (keys: 'chat', 'messages').
        Each message has 'author' (DIGEST) and 'message' fields.
        """

    @abstractmethod
    def individual_fidelity(self, chat: dict) -> None:
        """Evaluate how faithfully each agent's messages match its persona."""

    @abstractmethod
    def group_fidelity(self, chat: dict) -> None:
        """Evaluate how well the agents behave as a coherent group."""

    @abstractmethod
    def behavioural_fidelity(self, chat: dict) -> None:
        """Evaluate how human-like each agent's behaviour is in the chat."""
